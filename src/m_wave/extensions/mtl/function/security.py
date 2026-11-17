# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib

# third party
import pandas as pd

# local core
from m_wave.core.reporting.reporter import Reporter

# local extension
from m_wave.extensions.mtl.pdf_template import (
    ReportIssue,
)
from m_wave.extensions.mtl.utils.metadata import Metadata, TableType


class SecurityParser:
    """
    Parses and compares security strings.
    Takes the strings and builds permission map with a "principal key".
    Differences are reported to the journal and noted within the PDF report.
    """

    def __init__(self, reporter: Reporter, metadata: Metadata) -> None:
        self.reporter = reporter
        self.journal = reporter.journal
        self.notify = reporter.notifier
        self.debug = reporter.debug
        self.metadata = metadata
        self.canon_order = self.metadata.mtl_configs["canon_security_string_order"]

        # NOTE: use .clear() to reset list.
        self.report_issues: list[ReportIssue] = []

    def _issue(self, title: str, msg: str, severity: str = "error") -> None:
        """
        ReportIssue helper. Default severity = "error"
        """
        self.report_issues.append(ReportIssue(title, msg, severity))
        self.journal.error(msg)

    def normalize_permission(self, permission: str) -> str:
        """
        Normalizes one permission value.
        Whitespace removed, values in canonical PI order.
        """
        # Remove whitespace, tabs, etc
        permission = "".join(permission.split())

        try:
            before, content = permission.split("(", 1)
            rights, after = content.split(")", 1)
        except ValueError as e:
            message = f"Malformed permission value: {permission!r}"
            self._issue("Normalizing security value", message, "critical")
            raise ValueError(message) from e

        if rights == "":
            right_tokens = []
        else:
            right_tokens = rights.split(",")
            if any(not right for right in right_tokens):
                message = f"Malformed permission value: {permission!r}"
                self._issue("Normalizing security value", message, "critical")
                raise ValueError(message)

        # sort the rights
        right_set = set(right_tokens)
        unknown_rights = sorted(right_set - set(self.canon_order))

        if unknown_rights:
            message = (
                "Unknown permission right(s): "
                f"{', '.join(unknown_rights)}."
                "Comparison cannot safely normalize this value."
            )
            self._issue("Normalizing security value", message, "critical")
            raise ValueError(message)

        sorted_rights = ",".join(
            right for right in self.canon_order if right in right_set
        )

        return before + "(" + sorted_rights + ")" + after

    def canonicalize_security_string(self, text: str, record_name: str) -> str:
        """
        Normalizes a security string so that permission keys, and permission setting
        orders can be compared to correctly.
        """
        permissions = self.parse_security(text, record_name)
        canon = " | ".join(
            f"{principal}: {permissions[principal]}"
            for principal in sorted(permissions)
        )
        if canon:
            self.debug.debug("Canonized security string: %s", canon)
        return canon

    def parse_security(self, text: str, record_name: str) -> dict[str, str]:
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
                self._issue(
                    "Parser setting check",
                    f"Malformed security entry found in '{record_name}': {entry!r}. Cannot continue.",
                    "critical",
                )
                raise ValueError(
                    f"Malformed security entry found in '{record_name}': {entry!r}"
                )

            principal, permission = entry.split(":", 1)
            principal = principal.strip()
            permission = permission.strip()

            if not principal or not permission:
                raise ValueError(
                    f"Malformed security entry found in '{record_name}': {entry!r}"
                )

            # Don't silently overwrite repeated principals.
            if principal in result:
                raise ValueError(
                    f"Duplicate principal found in '{record_name}': {principal!r}"
                )

            result[principal] = self.normalize_permission(permission)

        return result

    def _get_matrix_column(
        self, canon_settings: dict | None, table_is_gxp: bool, column_name: str
    ) -> dict:
        """
        Returns the matrix dict that applies to the given column name.
        GxP tables keep onw matrix per security column (ptsecurity/datasecurity)
        Other tables return flat dicts or {}
        """
        if not isinstance(canon_settings, dict):
            return {}
        if table_is_gxp:
            canon_settings = canon_settings.get(column_name.strip().casefold())
        return canon_settings if isinstance(canon_settings, dict) else {}

    def _get_matrix_setting(
        self,
        canon_settings: dict | None,
        table_is_gxp: bool,
        column_name: str,
        principal: str,
    ) -> str:
        setting = "Not configured"

        settings = self._get_matrix_column(canon_settings, table_is_gxp, column_name)

        if not isinstance(canon_settings, dict):
            self.debug.debug(
                "No matrix settings for column '%s'. (principal '%s')",
                column_name,
                principal,
            )
            return setting

        # An exact key match takes precedence, including a literal "{server}" key.
        if principal in settings:
            return settings[principal]

        prefix = "PI Web API Admins ("
        if principal.startswith(prefix) and principal.endswith(")"):
            server = principal[len(prefix) : -1]
            configured_servers = {
                self.metadata.mtl_configs.get("val_server"),
                self.metadata.mtl_configs.get("prod_server"),
            }

            # Only use the template for a server configured as VAL or PROD.
            if server in configured_servers:
                template_key = "PI Web API Admins ({server})"
                expanded_key = template_key.format(server=server)

                if principal == expanded_key:
                    return settings.get(template_key, setting)

        return setting

    def compare_security_strings(
        self, record_name: str, column_name: str, mtl_string: str, pib_string: str
    ) -> dict:
        """
        Compare two security strings. Returns a dictionary of:
        ``matches``: boolean determination if the strings match,
        ``record_name``: record tested, can use keys or names
        ``column_name``: the specific security column name the string is from.
        ``only_in_mtl``: sorted permission keys only in the mtl string
        ``only_in_pib``: sorted permission keys only in the pi builder string
        ``only_in_matrix``: sorted permission keys only in the matrix string
        ``permission_differences``: dict of principal keys: {mtl_settings, pib_settings}
        ``mtl_only_settings``: dict of mtl only settings, principal: value
        ``pib_only_settings``: dict of pib only settings, principal: value
        ``matrix_only_settings``: dict of matrix only setting, principal: value
        """
        try:
            server_prefix = "PI Web API Admins ("
            server_key = "PI Web API Admins ({server})"

            table_type = self.metadata.get_table_type()
            formatting_rules = self.metadata.get_formatting_rules()
            table_is_gxp = table_type is TableType.GXP
            canon_settings = formatting_rules["Security Strings"]

            matrix = self._get_matrix_column(canon_settings, table_is_gxp, column_name)
            mtl = self.parse_security(mtl_string, record_name)
            pib = self.parse_security(pib_string, record_name)

            mtl_only = sorted(mtl.keys() - pib.keys())
            pib_only = sorted(pib.keys() - mtl.keys())
            mtl_only_settings = {principal: mtl[principal] for principal in mtl_only}
            pib_only_settings = {principal: pib[principal] for principal in pib_only}

            available_keys = mtl.keys() | pib.keys()
            server_key_present = any(
                principal.startswith(server_prefix) for principal in available_keys
            )

            matrix_only = sorted(
                key
                for key in matrix
                if key not in available_keys
                and not (key == server_key and server_key_present)
            )
            matrix_only_settings = {
                principal: self._get_matrix_setting(
                    canon_settings, table_is_gxp, column_name, principal
                )
                for principal in matrix_only
            }

            permission_differences = {
                principal: {
                    "mtl_setting": mtl[principal],
                    "pib_setting": pib[principal],
                    "matrix_setting": self._get_matrix_setting(
                        canon_settings, table_is_gxp, column_name, principal
                    ),
                }
                for principal in sorted(mtl.keys() & pib.keys())
                if mtl[principal] != pib[principal]
                or pib[principal] != matrix[principal]
            }

            all_settings = {
                principal: {
                    "mtl_setting": mtl.get(principal, "---"),
                    "pib_setting": pib.get(principal, "---"),
                    "matrix_setting": self._get_matrix_setting(
                        canon_settings, table_is_gxp, column_name, principal
                    ),
                }
                for principal in sorted(available_keys | set(matrix_only))
            }

            matches = not mtl_only and not pib_only and not permission_differences

            if not matches:
                self.journal.error_banner(
                    f"{record_name} security column: '{column_name}' has errors!"
                )
                if permission_differences:
                    for permission in permission_differences:
                        self.journal.error(
                            f"⛔ Permission '{permission}' has non matching values."
                        )

                    # self.journal.error("Matching Differences:")
                    # for permission, settings in permission_differences.items():
                    #     self.journal.error(f"\t{permission}:")
                    #     self.journal.error(
                    #         f"\t\tMTL_Setting: {settings['mtl_setting']}"
                    #     )
                    #     self.journal.error(
                    #         f"\t\tPIB_Setting: {settings['pib_setting']}"
                    #     )
                    #     matrix_setting = self._get_matrix_setting(
                    #         canon_settings,
                    #         table_is_non_standard,
                    #         column_name,
                    #         permission,
                    #     )
                    #     self.journal.error(f"\t\tMatrix_Setting: {matrix_setting}")

                if mtl_only:
                    for permission in mtl_only:
                        self.journal.error(
                            f"⛔ Permission '{permission}' is missing from the PI string"
                        )

                    # self.journal.error("Settings only in the MTL security string:")
                    # for permission in mtl_only:
                    #     self.journal.error(f"\t{permission}")

                if pib_only:
                    for permission in pib_only:
                        self.journal.error(
                            f"⛔ Permission '{permission}' is missing form the MTL string"
                        )

                    # self.journal.error(
                    #     "Settings only in the PI Builder security string:"
                    # )
                    # for permission in pib_only:
                    #     self.journal.error(f"\t{permission}")

            return {
                "matches": matches,
                "record_name": record_name,
                "column_name": column_name,
                "only_in_mtl": mtl_only,
                "only_in_pib": pib_only,
                "only_in_matrix": matrix_only,
                "permission_differences": permission_differences,
                "mtl_only_settings": mtl_only_settings,
                "pib_only_settings": pib_only_settings,
                "matrix_only_settings": matrix_only_settings,
                "all_settings": all_settings,
            }

        except Exception as e:
            msg = "An unexpected error occurred while attempting to compare security strings."
            self.debug.error(msg + ": %s", e)
            self.journal.error(msg)
            return {}

    def create_security_artifact(self, compared_security_strings: list[dict]):
        """
        Create a security string table artifact with a list of compared
        security string dictionaries.
        """

        columns = [
            "Record Name",
            "Security Column",
            "Permission",
            "MTL Config",
            "PIB Config",
            "Matrix Config",
            "MTL/CMD matches PI",
            "MTL/CMD matches Matrix",
            "PI matches Matrix",
            "Passes Validation",
        ]
        rows = []
        MISSING = "---"

        def build_row(common, principal, mtl_setting, pib_setting, matrix_setting):
            mtl_ok = mtl_setting == matrix_setting
            pib_ok = pib_setting == matrix_setting
            return {
                **common,
                "Permission": principal,
                "MTL Config": mtl_setting,
                "PIB Config": pib_setting,
                "Matrix Config": matrix_setting,
                "MTL/CMD matches PI": mtl_setting == pib_setting,
                "MTL/CMD matches Matrix": mtl_ok,
                "PI matches Matrix": pib_ok,
                "Passes Validation": pib_ok,
            }

        try:
            table_type = self.metadata.get_table_type()
            formatting_rules = self.metadata.get_formatting_rules()
            table_is_gxp = table_type is TableType.GXP
            canon_settings = formatting_rules["Security Strings"]

            for comparison in compared_security_strings:
                if not comparison or comparison.get("matches", True):
                    continue

                column_name = comparison["column_name"]
                common_fields = {
                    "Record Name": comparison["record_name"],
                    "Security Column": comparison["column_name"],
                }

                def _matrix_for(principal):
                    return self._get_matrix_setting(
                        canon_settings, table_is_gxp, column_name, principal
                    )

                for principal, setting in comparison.get("all_settings", {}).items():
                    rows.append(
                        build_row(
                            common_fields,
                            principal,
                            setting["mtl_setting"],
                            setting["pib_setting"],
                            setting["matrix_setting"],
                        )
                    )

                # for principal, setting in comparison.get(
                #     "permission_differences", {}
                # ).items():
                #     rows.append(
                #         build_row(
                #             common_fields,
                #             principal,
                #             setting["mtl_setting"],
                #             setting["pib_setting"],
                #             setting["matrix_setting"],
                #         )
                #     )
                #
                # for principal, mtl_setting in comparison.get(
                #     "mtl_only_settings", {}
                # ).items():
                #     rows.append(
                #         build_row(
                #             common_fields,
                #             principal,
                #             mtl_setting,
                #             MISSING,
                #             _matrix_for(principal),
                #         )
                #     )
                #
                # for principal, pib_setting in comparison.get(
                #     "pib_only_settings", {}
                # ).items():
                #     rows.append(
                #         build_row(
                #             common_fields,
                #             principal,
                #             MISSING,
                #             pib_setting,
                #             _matrix_for(principal),
                #         )
                #     )
                #
                # for principal, matrix_setting in comparison.get(
                #     "matrix_only_settings", {}
                # ).items():
                #     rows.append(
                #         build_row(
                #             common_fields,
                #             principal,
                #             MISSING,
                #             MISSING,
                #             matrix_setting,
                #         )
                #     )

            df = pd.DataFrame(rows, columns=columns)

            self.reporter.artifacts.save_csv(
                "compared_security_strings.csv",
                df,
                "A table of compared security strings. Reports differences and missing values.",
            )
        except Exception as e:
            self._issue(
                "Creating Security Artifact",
                "Could not create security artifact.",
                "critical",
            )
            self.debug.error(
                "An unexpected error occurred when attempting to create the security artifact, %s",
                e,
            )
