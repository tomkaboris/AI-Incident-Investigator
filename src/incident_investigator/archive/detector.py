import mimetypes
from pathlib import Path

ARCHIVE_SUFFIXES = (
    ".zip",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.bz2",
    ".tbz2",
    ".tar.xz",
    ".txz",
    ".gz",
    ".bz2",
    ".xz",
)
LOG_SUFFIXES = {
    ".log",
    ".txt",
    ".out",
    ".err",
    ".json",
    ".jsonl",
    ".csv",
    ".yaml",
    ".yml",
    ".xml",
    ".trace",
}


def is_archive_path(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(suffix) for suffix in ARCHIVE_SUFFIXES)


def content_type_for(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def detect_format(path: Path, sample: str) -> str:
    suffix = path.suffix.lower()
    stripped = sample.lstrip()
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".json" or (stripped.startswith("{") and stripped.endswith("}")):
        return "json"
    if suffix == ".csv":
        return "csv"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    if "Traceback (most recent call last)" in sample:
        return "python-traceback"
    if "AndroidRuntime" in sample or " logcat" in sample.lower():
        return "android-logcat"
    if "kubectl" in sample.lower() or "namespace=" in sample.lower():
        return "kubernetes"
    if "jenkins" in sample.lower() or "finished: failure" in sample.lower():
        return "jenkins-console"
    return "plain-text"


def detect_component(path: str, sample: str) -> str:
    text = (path + " " + sample[:2000]).lower()
    rules = (
        ("kubernetes", ("k8s", "kube", "pod", "container")),
        ("network", ("dns", "network", "tcp", "socket", "wifi")),
        ("database", ("mysql", "postgres", "database", "sql")),
        ("android", ("logcat", "androidruntime", "system_server")),
        ("kernel", ("dmesg", "kernel", "oom-killer")),
        ("ci-cd", ("jenkins", "pipeline", "build.log")),
        ("authentication", ("oauth", "authentication", "login", "token")),
        ("application", ("app", "service", "exception", "traceback")),
    )
    for component, words in rules:
        if any(word in text for word in words):
            return component
    return "unknown"
