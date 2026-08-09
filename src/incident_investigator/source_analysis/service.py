from __future__ import annotations

import logging
from pathlib import PurePath

from incident_investigator.config import Settings
from incident_investigator.integrations.github import GitHubClient, GitHubIntegrationError
from incident_investigator.source_analysis.extractor import (
    extract_error_search_terms,
    extract_source_hints,
)
from incident_investigator.source_analysis.models import (
    LogSourceHint,
    SourceAnalysis,
    SourceAnalysisStatus,
    SourceCandidate,
)

logger = logging.getLogger(__name__)


def _normalize_path(path: str | None) -> str:
    if not path:
        return ""
    return path.replace("\\", "/").lstrip("./")


def _suffix_match(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    normalized_left = _normalize_path(left).lower()
    normalized_right = _normalize_path(right).lower()
    return normalized_left.endswith(normalized_right) or normalized_right.endswith(normalized_left)


def _find_line(content: str, terms: list[str]) -> int | None:
    lowered_lines = [line.lower() for line in content.splitlines()]
    for term in terms:
        needle = term.lower().strip()
        if not needle:
            continue
        for index, line in enumerate(lowered_lines, start=1):
            if needle in line:
                return index
    return None


def _find_function_line(content: str, function: str | None) -> int | None:
    if not function:
        return None
    needle = function.lower()
    for index, line in enumerate(content.splitlines(), start=1):
        lowered = line.lower()
        if needle not in lowered:
            continue
        declaration_tokens = ("def ", "fun ", "void ", "public ", "private ", "class ")
        if any(token in lowered for token in declaration_tokens):
            return index
    return None


def _snippet(
    content: str,
    line_number: int | None,
    context_lines: int,
) -> tuple[int | None, int | None, str | None]:
    if not content:
        return None, None, None
    lines = content.splitlines()
    if not lines:
        return None, None, None
    center = line_number or 1
    center = max(1, min(center, len(lines)))
    start = max(1, center - context_lines)
    end = min(len(lines), center + context_lines)
    rendered = "\n".join(f"{number:>6}: {lines[number - 1]}" for number in range(start, end + 1))
    return start, end, rendered


def _with_line_fragment(url: str | None, start: int | None, end: int | None) -> str | None:
    if not url or not start:
        return url
    if end and end != start:
        return f"{url}#L{start}-L{end}"
    return f"{url}#L{start}"


def _fallback_analysis(hints: list[LogSourceHint], *, github_enabled: bool) -> SourceAnalysis:
    if hints:
        best = hints[0]
        return SourceAnalysis(
            status=SourceAnalysisStatus.INFERRED_FROM_LOG,
            provider="log",
            github_enabled=github_enabled,
            path=best.path,
            function=best.function,
            start_line=best.line_number,
            end_line=best.line_number,
            confidence=best.confidence,
            match_reason="File, function, or line information was extracted directly from the log.",
            explanation=(
                "This location is inferred from the uploaded log only and has not been verified "
                "against repository source code."
            ),
            inferred_hints=hints,
        )

    status = (
        SourceAnalysisStatus.NOT_FOUND
        if github_enabled
        else SourceAnalysisStatus.NOT_CONFIGURED
    )
    message = (
        "GitHub source lookup did not find a concrete source location."
        if github_enabled
        else (
            "GitHub source lookup is not configured and the log contains no concrete "
            "file/line hint."
        )
    )
    return SourceAnalysis(
        status=status,
        provider="log",
        github_enabled=github_enabled,
        confidence=0.0,
        lookup_message=message,
        inferred_hints=hints,
    )


async def _resolve_hit(
    *,
    client: GitHubClient,
    hit,
    hint: LogSourceHint | None,
    search_terms: list[str],
    settings: Settings,
) -> SourceCandidate | None:
    try:
        source_file = await client.get_file(
            owner=hit.owner,
            repository=hit.repository,
            path=hit.path,
            ref=settings.github_default_branch or None,
        )
    except GitHubIntegrationError:
        if settings.github_default_branch:
            try:
                source_file = await client.get_file(
                    owner=hit.owner,
                    repository=hit.repository,
                    path=hit.path,
                    ref=None,
                )
            except GitHubIntegrationError:
                return None
        else:
            return None

    line_number = hint.line_number if hint else None
    reasons: list[str] = []
    score = 0.2
    source_line_count = max(1, len(source_file.content.splitlines()))

    if hint:
        if hint.filename and hit.name.lower() == hint.filename.lower():
            score += 0.35
            reasons.append("stack-trace filename match")
        if _suffix_match(hint.path, hit.path):
            score += 0.2
            reasons.append("stack-trace path match")
        function_line = None
        if hint.function and hint.function.lower() in source_file.content.lower():
            score += 0.1
            reasons.append("function/symbol match")
            function_line = _find_function_line(source_file.content, hint.function)
            if line_number is None:
                line_number = function_line
        if line_number is not None and line_number > source_line_count:
            score = max(0.0, score - 0.15)
            reasons.append("reported line is outside the current file revision")
            line_number = function_line

    matched_error_line = _find_line(source_file.content, search_terms)
    if matched_error_line:
        score += 0.25
        reasons.append("exact error-text match")
        if line_number is None:
            line_number = matched_error_line

    if not reasons:
        reasons.append("GitHub code-search candidate")

    start, end, snippet = _snippet(
        source_file.content,
        line_number,
        settings.github_context_lines,
    )
    return SourceCandidate(
        repository=source_file.repository,
        owner=source_file.owner,
        path=source_file.path,
        ref=settings.github_default_branch or None,
        content_sha=source_file.sha,
        function=hint.function if hint else None,
        start_line=start,
        end_line=end,
        snippet=snippet,
        source_url=_with_line_fragment(source_file.html_url, start, end),
        confidence=min(score, 0.99),
        match_reason=", ".join(reasons),
    )


async def analyze_source_location(
    log_text: str,
    settings: Settings,
    *,
    client: GitHubClient | None = None,
) -> SourceAnalysis:
    """Infer and, when enabled, verify the likely source location for an incident."""
    hints = extract_source_hints(log_text)
    search_terms = extract_error_search_terms(log_text)
    github_enabled = bool(settings.github_enabled and settings.github_source_lookup_enabled)

    if not github_enabled:
        return _fallback_analysis(hints, github_enabled=False)

    if not settings.github_token:
        result = _fallback_analysis(hints, github_enabled=True)
        result.status = SourceAnalysisStatus.LOOKUP_FAILED
        result.lookup_message = "GitHub source lookup is enabled but GITHUB_TOKEN is missing."
        return result

    client = client or GitHubClient.from_settings(settings)
    search_queries: list[tuple[str, LogSourceHint | None]] = []
    seen_queries: set[str] = set()

    for hint in hints[:4]:
        if not hint.filename:
            continue
        query = f"filename:{PurePath(hint.filename).name}"
        if query not in seen_queries:
            search_queries.append((query, hint))
            seen_queries.add(query)

    for term in search_terms[:4]:
        escaped = term.replace('"', "")
        query = f'"{escaped}"'
        if query not in seen_queries:
            search_queries.append((query, hints[0] if hints else None))
            seen_queries.add(query)

    if not search_queries:
        return _fallback_analysis(hints, github_enabled=True)

    candidates: list[SourceCandidate] = []
    try:
        resolved_keys: set[tuple[str, str, str]] = set()
        for query, hint in search_queries[: settings.github_max_queries]:
            hits = await client.search_code(query)
            for hit in hits:
                hit_key = (hit.owner, hit.repository, hit.path)
                if hit_key in resolved_keys:
                    continue
                if len(resolved_keys) >= settings.github_max_candidates:
                    break
                resolved_keys.add(hit_key)
                candidate = await _resolve_hit(
                    client=client,
                    hit=hit,
                    hint=hint,
                    search_terms=search_terms,
                    settings=settings,
                )
                if candidate:
                    candidates.append(candidate)
    except GitHubIntegrationError as exc:
        logger.warning("GitHub source lookup failed: %s", exc)
        result = _fallback_analysis(hints, github_enabled=True)
        result.status = SourceAnalysisStatus.LOOKUP_FAILED
        result.lookup_message = str(exc)
        return result

    unique: dict[tuple[str, str, str], SourceCandidate] = {}
    for candidate in candidates:
        key = (candidate.owner or "", candidate.repository, candidate.path)
        existing = unique.get(key)
        if existing is None or candidate.confidence > existing.confidence:
            unique[key] = candidate

    ranked = sorted(unique.values(), key=lambda item: item.confidence, reverse=True)
    if not ranked:
        return _fallback_analysis(hints, github_enabled=True)

    best = ranked[0]
    close_candidates = [item for item in ranked if best.confidence - item.confidence <= 0.08]
    status = (
        SourceAnalysisStatus.MULTIPLE_CANDIDATES
        if len(close_candidates) > 1
        else SourceAnalysisStatus.RESOLVED
    )
    explanation = (
        "The location was verified against source code accessible through GitHub/GHE."
        if status == SourceAnalysisStatus.RESOLVED
        else (
            "Several repository locations match the available log evidence; human "
            "review is recommended."
        )
    )

    provider = (
        "github"
        if getattr(client, "api_url", "").rstrip("/") == "https://api.github.com"
        else "github_enterprise"
    )

    return SourceAnalysis(
        status=status,
        provider=provider,
        github_enabled=True,
        repository=best.repository,
        owner=best.owner,
        path=best.path,
        ref=best.ref,
        content_sha=best.content_sha,
        function=best.function,
        start_line=best.start_line,
        end_line=best.end_line,
        snippet=best.snippet,
        source_url=best.source_url,
        confidence=best.confidence,
        match_reason=best.match_reason,
        explanation=explanation,
        inferred_hints=hints,
        candidates=ranked[:5],
    )


def source_context_for_prompt(source_analysis: SourceAnalysis) -> str:
    """Render bounded source-location evidence for AI correlation prompts."""
    if source_analysis.status in {
        SourceAnalysisStatus.NOT_CONFIGURED,
        SourceAnalysisStatus.NOT_FOUND,
        SourceAnalysisStatus.LOOKUP_FAILED,
    } and not source_analysis.path:
        return "No verified source-code context is available."

    parts = [
        f"Status: {source_analysis.status.value}",
        f"Provider: {source_analysis.provider}",
        f"Repository: {source_analysis.repository or 'unknown'}",
        f"Path: {source_analysis.path or 'unknown'}",
        f"Function: {source_analysis.function or 'unknown'}",
        f"Lines: {source_analysis.start_line or 'unknown'}-{source_analysis.end_line or 'unknown'}",
        f"Confidence: {source_analysis.confidence:.2f}",
        f"Match reason: {source_analysis.match_reason or 'unknown'}",
    ]
    if source_analysis.snippet:
        parts.extend(
            ["Source snippet:", "<source_code>", source_analysis.snippet, "</source_code>"]
        )
    return "\n".join(parts)


async def safe_analyze_source_location(log_text: str, settings: Settings) -> SourceAnalysis:
    """Never let optional source-code correlation fail the core incident workflow."""
    try:
        return await analyze_source_location(log_text, settings)
    except Exception as exc:  # defensive boundary around an optional external integration
        logger.warning("Source-code correlation failed unexpectedly: %s", type(exc).__name__)
        hints = extract_source_hints(log_text)
        result = _fallback_analysis(
            hints,
            github_enabled=bool(settings.github_enabled and settings.github_source_lookup_enabled),
        )
        result.status = SourceAnalysisStatus.LOOKUP_FAILED
        result.lookup_message = f"Source lookup failed: {type(exc).__name__}"
        return result
