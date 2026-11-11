# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib

# local core
from m_wave.core.reporting.reporter import Reporter

# local extension
from m_wave.extensions.mtl.pdf_template import (
    ReportIssue,
)
from m_wave.extensions.mtl.utils.metadata import Metadata


class SecurityParser:
    """
    Parses and compares secuirty strings.
    Takes the strings and builds permission map with a "principal key".
    Differences are reported to the journal and noted within the PDF report.
    """

    def __init__(self, reporter: Reporter, metadata: Metadata) -> None:
        self.reporter = reporter
        self.journal = reporter.journal
        self.notify = reporter.notifier
        self.debug = reporter.debug

        self.metadata = metadata

        self.pib_string: str = ""
        self.mtl_string: str = ""

        self.result: bool = False

        # NOTE: use .clear() to reset list.
        self.report_issues: list[ReportIssue] = []

    def canonicalize_security_string(self, text: str) -> str:
        """
        Normalizes a security string so that permission keys, and permission setting
        orders can be compared to correctly.
        """
        permissions = self.parse_security(text)
        canon = " | ".join(
            f"{principal}: {permissions[principal]}"
            for principal in sorted(permissions)
        )
        self.debug.debug("Cannonized security string: %s", canon)
        return canon

    def normalize_permission(self, permission: str) -> str:
        """
        Normalizes the whitespace and sorts the order of rights inside
        the parantheses as irrelivant: A(r,w) becomes the same as A(w,r)
        """
        # Remove whitespace, tabs, etc
        permission = "".join(permission.split())

        before, content = permission.split("(", 1)
        rights, after = content.split(")", 1)

        # sort the rights
        sorted_rights = ",".join(sorted(rights.split(",")))

        return before + "(" + sorted_rights + ")" + after

    def parse_security(self, text: str) -> dict[str, str]:
        """
        Build the security map. Uses a security type as the principal key,
        then assigns values as strings.
        """
        # Some copied reports use non-breaking spaces.
        text = text.replace("\u00a0", " ")

        result = {}

        for entry in text.split("|"):
            entry = entry.strip()
            if not entry:
                continue

            if ":" not in entry:
                msg = f"Malformed security entry: {entry!r}. Cannot continue."
                issue = ReportIssue("Parser setting check", msg, "critical")
                self.report_issues.append(issue)
                self.journal.error(msg)
                raise ValueError(f"Malformed security entry: {entry!r}")

            principal, permission = entry.split(":", 1)
            principal = principal.strip()
            permission = permission.strip()

            if not principal or not permission:
                raise ValueError(f"Malformed security entry: {entry!r}")

            # Don't silently overwrite repeated principals.
            if principal in result:
                raise ValueError(f"Duplicate principal: {principal!r}")

            result[principal] = self.normalize_permission(permission)

        return result

    def compare_security_strings(
        self, record_name: str, column_name: str, mtl_string: str, pib_string: str
    ) -> dict:
        """
        Compare two security strings. Returns a dictionary of:
        ``matches``: boolean determination if the strings match,
        ``record_name``: record tested, can use keys or names
        ``column_name``: the specific security column name the string is from.
        ``only_in_mtl``: sorted permission keys only in the mtl string,
        ``only_in_pi_builder``: sorted permission skeys only in the pi builder string,
        ``permission_differences``: dict of principal keys: {mtl_settings, pib_settings}
        """
        try:
            mtl = self.parse_security(mtl_string)
            pib = self.parse_security(pib_string)

            mtl_only = sorted(mtl.keys() - pib.keys())
            pib_only = sorted(pib.keys() - mtl.keys())

            permission_differences = {
                principal: {
                    "mtl_setting": mtl[principal],
                    "pib_setting": pib[principal],
                }
                for principal in sorted(mtl.keys() & pib.keys())
                if mtl[principal] != pib[principal]
            }

            matches = not mtl_only and not pib_only and not permission_differences

            if not matches:
                self.journal.error_banner(
                    f"{record_name}: '{column_name}' string does not match!"
                )
                if permission_differences:
                    self.journal.error("Matching Differences:")
                    for permission, settings in permission_differences.items():
                        self.journal.error(f"\t{permission}:")
                        self.journal.error(
                            f"\t\tMTL_Setting: {settings['mtl_setting']}"
                        )
                        self.journal.error(
                            f"\t\tPIB_Setting: {settings['pib_setting']}"
                        )

                if mtl_only:
                    self.journal.error("Settings only in the MTL security string:")
                    for permission in mtl_only:
                        self.journal.error(f"\t{permission}")

                if pib_only:
                    self.journal.error(
                        "Settings only in the PI Builder security string:"
                    )
                    for permission in pib_only:
                        self.journal.error(f"\t{permission}")

            return {
                "matches": matches,
                "record_name": record_name,
                "column_name": column_name,
                "only_in_mtl": mtl_only,
                "only_in_pi_builder": pib_only,
                "permission_differences": permission_differences,
            }
        except Exception as e:
            msg = "An unexpected error occurred while attempting to compare security strings."
            self.debug.error(msg + ": %s", e)
            self.journal.error(msg)
            return {}
