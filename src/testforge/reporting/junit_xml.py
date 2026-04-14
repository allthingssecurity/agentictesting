"""JUnit XML report writer — CI-compatible format."""

import xml.etree.ElementTree as ET
from pathlib import Path

from testforge.models.evidence import Report


def write_junit_xml(report: Report, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    testsuites = ET.Element("testsuites")
    testsuites.set("name", "TestForge")
    testsuites.set("tests", str(len(report.results)))

    # Group by test_type
    by_type: dict[str, list] = {}
    for r in report.results:
        by_type.setdefault(r.test_type, []).append(r)

    for test_type, results in by_type.items():
        suite = ET.SubElement(testsuites, "testsuite")
        suite.set("name", test_type)
        suite.set("tests", str(len(results)))
        failures = sum(1 for r in results if r.status in ("failed", "error"))
        suite.set("failures", str(failures))

        for r in results:
            tc = ET.SubElement(suite, "testcase")
            tc.set("name", r.name)
            tc.set("classname", f"{test_type}.{r.language or 'unknown'}")
            tc.set("time", f"{r.duration_ms / 1000:.3f}")

            if r.status in ("failed", "error"):
                failure = ET.SubElement(tc, "failure")
                failure.set("message", r.message[:500])
                failure.set("type", r.status)
                failure.text = r.message
            elif r.status == "skipped":
                ET.SubElement(tc, "skipped")

    tree = ET.ElementTree(testsuites)
    path = output_dir / "junit.xml"
    tree.write(str(path), encoding="unicode", xml_declaration=True)
    return path
