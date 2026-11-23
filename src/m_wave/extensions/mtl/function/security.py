# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib

# third party
import re

import pandas as pd

# local core
from m_wave.core.reporting.reporter import Reporter

# local extension
from m_wave.extensions.mtl.pdf_template import (
    ReportIssue,
)
from m_wave.extensions.mtl.utils.metadata import Metadata, TableType

PI_TAG_TABLES = [TableType.GXP, TableType.ANALYTICS]


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

    def remove_permeable_permissions(self, permission: str) -> str:
        """
        Elements and Element Templates will often keep permissions
        (r, x, s, and so) in principal permissions. This rebuilds the
        permissions to remove them.
        """
        permission = "".join(permission.split())
        permeable_values = self.metadata.get_worksheet_permeable_permission_values()

        try:
            before, content = permission.split("(")
            rights, after = content.split(")")

            tokens = rights.split(",")
            for permeable in permeable_values:
                if permeable in tokens:
                    tokens.remove(permeable)
            right_set = set(tokens)
            sorted_rights = ",".join(
                right for right in self.canon_order if right in right_set
            )
            modified = before + "(" + sorted_rights + ")" + after
            return modified

        except Exception as e:
            msg = f"Could not remove permeable permissions from '{permission}'"
            self.journal.error(msg)
            self.debug.error(msg + ": %s", e, error=e)
            raise ValueError(msg)

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

    def canonicalize_security_string(
        self,
        text: str,
        column_name: str,
    ) -> str:
        """
        Normalizes a security string so that permission keys, and permission setting
        orders can be compared to correctly.
        """
        permissions = self.parse_security(text, column_name)
        matrix = self._matrix_for_column(column_name)
        permissions = self._drop_other_site_principals(permissions, matrix)

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

            compact_permission = "".join(permission.split())
            action, is_valid, _ = compact_permission.partition("(")
            if is_valid and action.upper() != "A":
                self.debug.debug(
                    "Ignoring deny permission for principal %s in %s",
                    principal,
                    record_name,
                )
                continue

            # Don't silently overwrite repeated principals.
            if principal in result:
                raise ValueError(
                    f"Duplicate principal '{principal!r}' found in '{record_name!r}'"
                )

            result[principal] = self.normalize_permission(permission)

        return result

    def _get_matrix_column(
        self, canon_settings: dict | None, is_tag_table: bool, column_name: str
    ) -> dict:
        """
        Returns the matrix dict that applies to the given column name.
        GxP, and Analytic tables keep one matrix per security column
        (ptsecurity/datasecurity)
        Other tables return flat dicts or {}
        """
        if not isinstance(canon_settings, dict):
            return {}
        if is_tag_table:
            canon_settings = canon_settings.get(column_name.strip().casefold())
        return canon_settings if isinstance(canon_settings, dict) else {}

    def _get_matrix_setting(
        self,
        canon_settings: dict | None,
        is_tag_table: bool,
        column_name: str,
        principal: str,
    ) -> str:
        setting = "Not configured"

        settings = self._get_matrix_column(canon_settings, is_tag_table, column_name)

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

    def _matrix_for_column(self, column_name: str) -> dict:
        rules = self.metadata.get_formatting_rules()
        return self._get_matrix_column(
            rules["Security Strings"],
            self.metadata.get_table_type() in [TableType.GXP, TableType.ANALYTICS],
            column_name,
        )

    def _drop_other_site_principals(
        self,
        permissions: dict[str, str],
        matrix: dict,
    ) -> dict[str, str]:
        in_scope_codes = set()
        site_code_principal = re.compile(r"^PI_([A-Z0-9]{2,8})_")
        for principal in matrix:
            match = site_code_principal.match(principal)
            if match:
                in_scope_codes.add(match.group(1))

        if not in_scope_codes:
            return permissions

        filtered = {}
        dropped = []
        for principal, setting in permissions.items():
            match = site_code_principal.match(principal)
            if match and match.group(1) not in in_scope_codes:
                dropped.append(principal)
            else:
                filtered[principal] = setting
        if dropped:
            self.debug.debug(
                "Ignoring permissions for other site codes: %s", sorted(dropped)
            )

        return filtered

    def compare_security_strings(
        self,
        record_name: str,
        column_name: str,
        mtl_string: str,
        pib_string: str,
    ) -> dict:
        """
        Compare one MTL/CMD security string with its PI Builder string, and the PI
        Builder string with the security matrix.

        The two checks are reported separately:

        ``mtl_matches_pi``: the MTL/CMD and PI strings grant the same principals the
            same permissions. Uses effective permissions on worksheets with
            permeable permissions.
        ``pi_matches_matrix``: every principal in the PI string, and every principal
            the matrix expects, has the permission the matrix requires.
        ``passes``: both checks passed.

        Supporting detail:

        ``record_name``: record tested, can use keys or names.
        ``column_name``: the security column the strings are from.
        ``only_in_mtl``: sorted principals only in the MTL/CMD string.
        ``only_in_pib``: sorted principals only in the PI Builder string.
        ``only_in_matrix``: sorted principals only in the matrix.
        ``mtl_pi_differences``: principals in both strings whose permissions differ,
            {principal: {"mtl_setting", "pib_setting"}}.
        ``pi_matrix_differences``: principals whose PI permission does not satisfy
            the matrix, {principal: {"pib_setting", "matrix_setting"}}.
        ``mtl_only_settings`` / ``pib_only_settings`` / ``matrix_only_settings``:
            {principal: setting} for the one-sided principals above.
        ``all_settings``: every principal with its raw MTL, PI, and matrix settings.
        ``permeable_settings``: original and effective settings per principal, only
            populated on worksheets with permeable permissions.

        Returns an empty dict when the strings cannot be evaluated.
        """
        missing = "---"

        try:
            server_prefix = "PI Web API Admins ("
            server_key = "PI Web API Admins ({server})"

            table_type = self.metadata.get_table_type()
            formatting_rules = self.metadata.get_formatting_rules()
            is_tag_table = table_type in PI_TAG_TABLES
            canon_settings = formatting_rules["Security Strings"]
            has_permeable = self.metadata.worksheet_has_permeable_permissions()

            matrix = self._get_matrix_column(canon_settings, is_tag_table, column_name)

            def matrix_setting(principal: str) -> str:
                return self._get_matrix_setting(
                    canon_settings, is_tag_table, column_name, principal
                )

            def effective_setting(settings: dict[str, str], principal: str) -> str:
                """The setting actually compared: permeable rights removed if needed."""
                original = settings.get(principal, missing)
                if original == missing or not has_permeable:
                    return original
                return self.remove_permeable_permissions(original)

            mtl = self._drop_other_site_principals(
                self.parse_security(mtl_string, record_name), matrix
            )
            pib = self._drop_other_site_principals(
                self.parse_security(pib_string, record_name), matrix
            )

            # -- principals present on one side only ------------------------
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
                principal: matrix_setting(principal) for principal in matrix_only
            }
            all_principals = sorted(available_keys | set(matrix_only))

            # -- check 1: MTL/CMD vs PI -------------------------------------
            mtl_pi_differences = {
                principal: {
                    "mtl_setting": effective_setting(mtl, principal),
                    "pib_setting": effective_setting(pib, principal),
                }
                for principal in sorted(mtl.keys() & pib.keys())
                if effective_setting(mtl, principal)
                != effective_setting(pib, principal)
            }
            mtl_matches_pi = not mtl_only and not pib_only and not mtl_pi_differences

            # -- check 2: PI vs security matrix -----------------------------
            pi_matrix_differences = {
                principal: {
                    "pib_setting": effective_setting(pib, principal),
                    "matrix_setting": matrix_setting(principal),
                }
                for principal in all_principals
                if effective_setting(pib, principal) != matrix_setting(principal)
            }
            pi_matches_matrix = not pi_matrix_differences

            # -- detail for the security artifact ---------------------------
            all_settings = {
                principal: {
                    "mtl_setting": mtl.get(principal, missing),
                    "pib_setting": pib.get(principal, missing),
                    "matrix_setting": matrix_setting(principal),
                }
                for principal in all_principals
            }
            permeable_settings = (
                {
                    principal: {
                        "mtl_setting_original": mtl.get(principal, missing),
                        "mtl_setting_effective": effective_setting(mtl, principal),
                        "pib_setting_original": pib.get(principal, missing),
                        "pib_setting_effective": effective_setting(pib, principal),
                        "matrix_setting": matrix_setting(principal),
                    }
                    for principal in all_principals
                }
                if has_permeable
                else {}
            )

            self._log_security_findings(
                record_name,
                column_name,
                mtl_only,
                pib_only,
                matrix_only,
                mtl_pi_differences,
                pi_matrix_differences,
            )

            return {
                "mtl_matches_pi": mtl_matches_pi,
                "pi_matches_matrix": pi_matches_matrix,
                "passes": mtl_matches_pi and pi_matches_matrix,
                "record_name": record_name,
                "column_name": column_name,
                "only_in_mtl": mtl_only,
                "only_in_pib": pib_only,
                "only_in_matrix": matrix_only,
                "mtl_pi_differences": mtl_pi_differences,
                "pi_matrix_differences": pi_matrix_differences,
                "mtl_only_settings": mtl_only_settings,
                "pib_only_settings": pib_only_settings,
                "matrix_only_settings": matrix_only_settings,
                "all_settings": all_settings,
                "permeable_settings": permeable_settings,
            }

        except Exception as e:
            msg = "An unexpected error occurred while attempting to compare security strings."
            self.debug.error(msg + ": %s", e, error=e)
            self.journal.error(msg)
            self.journal.error(f"Error: {e}")
            return {}

    def _log_security_findings(
        self,
        record_name: str,
        column_name: str,
        mtl_only: list[str],
        pib_only: list[str],
        matrix_only: list[str],
        mtl_pi_differences: dict[str, dict[str, str]],
        pi_matrix_differences: dict[str, dict[str, str]],
    ) -> None:
        """Journal each failed check under its own heading."""
        mtl_pi_failed = bool(mtl_only or pib_only or mtl_pi_differences)
        pi_matrix_failed = bool(pi_matrix_differences)
        if not (mtl_pi_failed or pi_matrix_failed):
            return

        self.journal.error_banner(
            f"{record_name} security column: '{column_name}' has errors!"
        )

        if mtl_pi_failed:
            self.journal.error("MTL/CMD vs PI:")
            for principal, setting in mtl_pi_differences.items():
                self.journal.error(
                    f"⛔ Permission '{principal}' differs: MTL/CMD "
                    f"{setting['mtl_setting']} vs PI {setting['pib_setting']}"
                )
            for principal in mtl_only:
                self.journal.error(
                    f"⛔ MTL/CMD permission '{principal}' is missing from the PI string"
                )
            for principal in pib_only:
                self.journal.error(
                    f"⛔ PI permission '{principal}' is missing from the MTL/CMD string"
                )

        if pi_matrix_failed:
            self.journal.error("PI vs security matrix:")
            for principal, setting in pi_matrix_differences.items():
                if principal in matrix_only:
                    self.journal.error(
                        f"⛔ Matrix permission '{principal}' "
                        f"({setting['matrix_setting']}) is missing from the PI string"
                    )
                else:
                    self.journal.error(
                        f"⛔ Permission '{principal}' does not satisfy the matrix: PI "
                        f"{setting['pib_setting']} vs matrix "
                        f"{setting['matrix_setting']}"
                    )

    def _announce_effective_settings(self) -> None:
        """
        Explain effective configurations in the journal and a notification.

        This used to be a note row at the top of the security artifact, but a
        row with only a "Record Name" left every other column blank, so tools
        reading the CSV saw "Passes Validation" as False and counted a failure.
        """
        permeable_values = self.metadata.get_worksheet_permeable_permission_values()
        values = ", ".join(f"'{value}'" for value in permeable_values or [])
        message = (
            "This worksheet uses permeable permissions. Effective configurations "
            f"remove permeable settings ({values}) so that comparisons reference "
            "active permission values only. The 'Effective Config' columns in "
            "compared_security_strings.csv show the values that were compared."
        )
        self.journal.info(message)
        self.notify.info(message, "Effective security configurations")

    def create_security_dataframe(
        self, compared_security_strings: list[dict]
    ) -> pd.DataFrame:
        """
        Create a security string table artifact with a list of compared
        security string dictionaries.
        """
        columns = (
            [
                "Record Name",
                "Security Column",
                "Permission",
                "MTL/CMD Config",
                "PI System Config",
                "Security Matrix Config",
                "MTL/CMD matches PI System",
                "MTL/CMD matches Security Matrix",
                "PI System matches Security Matrix",
                "Passes Validation",
            ]
            if not self.metadata.worksheet_has_permeable_permissions()
            else [
                "Record Name",
                "Security Column",
                "Permission",
                "MTL/CMD Original Config",
                "MTL/CMD Effective Config",
                "PI System Original Config",
                "PI System Effective Config",
                "Security Matrix Config",
                "MTL/CMD matches PI System",
                "MTL/CMD matches Security Matrix",
                "PI System matches Security Matrix",
                "Passes Validation",
            ]
        )
        rows = []

        def _build_row(
            is_permeable: bool,
            common,
            principal,
            mtl_setting,
            pib_setting,
            matrix_setting,
            mtl_effective="",
            pib_effective="",
        ) -> dict:
            """
            Builds a dictionary that is used to create a record (row) for the dataframe.
            """
            row = {
                **common,
                "Permission": principal,
                "MTL/CMD Config": mtl_setting,
                "PI System Config": pib_setting,
                "Security Matrix Config": matrix_setting,
                "MTL/CMD matches PI System": mtl_setting == pib_setting,
                "MTL/CMD matches Security Matrix": mtl_setting == matrix_setting,
                "PI System matches Security Matrix": pib_setting == matrix_setting,
                "Passes Validation": pib_setting == matrix_setting,
            }
            permeable_row = {
                **common,
                "Permission": principal,
                "MTL/CMD Original Config": mtl_setting,
                "MTL/CMD Effective Config": mtl_effective,
                "PI System Original Config": pib_setting,
                "PI System Effective Config": pib_effective,
                "Security Matrix Config": matrix_setting,
                "MTL/CMD matches PI System": mtl_effective == pib_effective,
                "MTL/CMD matches Security Matrix": mtl_effective == matrix_setting,
                "PI System matches Security Matrix": pib_effective == matrix_setting,
                "Passes Validation": pib_effective == matrix_setting,
            }
            return permeable_row if is_permeable else row

        try:
            table_type = self.metadata.get_table_type()
            formatting_rules = self.metadata.get_formatting_rules()
            is_tag_table = table_type in PI_TAG_TABLES
            canon_settings = formatting_rules["Security Strings"]

            for comparison in compared_security_strings:
                if not comparison:
                    continue

                common_fields = {
                    "Record Name": comparison["record_name"],
                    "Security Column": comparison["column_name"],
                }

                def _matrix_for(principal, column_name):
                    return self._get_matrix_setting(
                        canon_settings, is_tag_table, column_name, principal
                    )

                if self.metadata.worksheet_has_permeable_permissions():
                    for principal, setting in comparison.get(
                        "permeable_settings", {}
                    ).items():
                        rows.append(
                            _build_row(
                                True,
                                common_fields,
                                principal,
                                setting["mtl_setting_original"],
                                setting["pib_setting_original"],
                                setting["matrix_setting"],
                                setting["mtl_setting_effective"],
                                setting["pib_setting_effective"],
                            )
                        )

                else:
                    for principal, setting in comparison.get(
                        "all_settings", {}
                    ).items():
                        rows.append(
                            _build_row(
                                False,
                                common_fields,
                                principal,
                                setting["mtl_setting"],
                                setting["pib_setting"],
                                setting["matrix_setting"],
                            )
                        )
            if self.metadata.worksheet_has_permeable_permissions():
                self._announce_effective_settings()

            return pd.DataFrame(rows, columns=columns)

            # self.reporter.artifacts.save_csv(
            #     "compared_security_strings.csv",
            #     df,
            #     "A table of compared security strings. Reports differences and missing values.",
            # )

        except Exception as e:
            self._issue(
                "Creating Security Artifact",
                "Could not create security artifact.",
                "critical",
            )
            self.debug.error(
                "An unexpected error occurred when attempting to create the security artifact, %s",
                e,
                error=e,
            )
