# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from threading import Thread

# third-party
import ttkbootstrap as tkb
from ttkbootstrap.constants import DISABLED, NORMAL

# local core
from m_wave.core.context import AppContext
from m_wave.core.utils import load_configs
from m_wave.core.wavepacks.controller import WavePackController

# local wave pack
from m_wave.extensions.mtl.processor import MTLProcessor
from m_wave.extensions.mtl.utils.paths import get_mtl_config_path
from m_wave.extensions.mtl.utils.utils import (
    MTLProcessorRequest,
    MTLProcessorType,
    MTLUiPayload,
)


class MTLController(WavePackController):
    """
    Master thread controller of the reporting, processing and configuration parsing.
    """

    def __init__(self, app: tkb.Window, context: AppContext):
        super().__init__(app, context)
        self.processor = MTLProcessor(self.reporter)
        self.journal = self.reporter.journal
        self.debug = self.reporter.debug
        self.notify = self.reporter.notifier
        self.context: AppContext = context

        try:
            self.configs = load_configs(get_mtl_config_path())
        except Exception as e:
            msg = f"Could not load configurations, check the general log file: {e}"
            self.journal.error(msg)
            self.notify.error(msg)

    def start_process(self, request: MTLProcessorRequest, ui: MTLUiPayload) -> None:
        """
        Called on the main thread when the user clicks the process button.
        """
        if self.is_running:
            self.notify.warning("Process already running!")
            return

        self.display_journal_to(ui.text_box)

        if request.process_type == MTLProcessorType.APPEND:
            self.notify.info("This process is currently disabled.")
            return

        ui.process_button.config(state=DISABLED)
        ui.progress_bar.start()

        self.process_thread = Thread(
            target=self._worker_thread,
            args=(request, ui),
            name="MTLProcessor",
            daemon=True,
        )
        self.process_thread.start()

    def _worker_thread(self, request: MTLProcessorRequest, ui: MTLUiPayload) -> None:
        """
        Worker thread for one completed process run.
            start_process -> processor.run -> report.finish (or report.finish_with_error)
        """
        reporter = self.reporter
        try:
            report_name = str(
                request.report_name
                if request.report_name is not None
                else "Unfiltered Report"
            )
            report = reporter.start_report(report_name)
            if request.process_type == MTLProcessorType.DOWNLOAD:
                pdf_template = self.processor.download_mtl(request, ui)
                reporter.finish_report(pdf_template)
                reporter.notifier.info(
                    f"Process finished: {pdf_template.status.label}\n"
                    f"Results saved to: {report.folder.name}"
                )
            elif request.process_type == MTLProcessorType.COMPARE:
                pdf_template = self.processor.run_comparison(request, ui)
                reporter.finish_report(pdf_template)
                reporter.notifier.info(
                    f"Process finished: {pdf_template.status.label}\n"
                    f"Results saved to : {report.folder.name}"
                )
            else:
                self.notify.info(
                    "How... did you get here? No processor type was found, but the app attempted to process something."
                )

        except Exception as error:
            reporter.finish_report_with_error(error)
            self.notify.error(
                f"The process stopped with an unexpected error:\n{error}\n\n"
                "See journal.log in the report folder for more details."
            )
        finally:
            self.app.after(0, ui.progress_bar.stop)
            self.app.after(0, lambda: ui.process_button.config(state=NORMAL))

    # def _start_thread(
    #     self,
    #     req: MTLRequest,
    #     ui: MTLUi,
    # ) -> None:
    #     """
    #     Opens a new thread and starts the subroutine.
    #     """
    #     _started = time.perf_counter()
    #     if self.report is not None:
    #         try:
    #             process = Process(
    #                 self.report,
    #                 req.filter,
    #                 req.data_table,
    #                 req.env_types,
    #                 req.mtl_file_path,
    #                 req.input_file_path,
    #             )
    #
    #             if req.process_type == MTLProcessorType.APPEND:
    #                 process.run_append()
    #             elif req.process_type == MTLProcessorType.COMPARE:
    #                 process.run_comparison()
    #             elif req.process_type == MTLProcessorType.DOWNLOAD:
    #                 process.get_mtl_from_web(ui.version_var, ui.mtl_path)
    #             else:
    #                 self.report.critical(
    #                     "Process request failed. MTLProcessorType does not exist",
    #                     popup=True,
    #                 )
    #
    #         except Exception as e:
    #             self.report.exception(
    #                 f"Subroutine process error:\n{e}",
    #                 popup=True,
    #             )
    #         finally:
    #             _ended = time.perf_counter()
    #
    #             def _finish_ui():
    #                 ui.progress_bar.stop()
    #                 ui.opt_process.set(MTLProcessorType.NONE)
    #                 ui.process_button.config(state=NORMAL)
    #
    #             self.app.after(
    #                 0, lambda r=self.report: r.info("Subroutine ended.", popup=True)
    #             )
    #             self.app.after_idle(_finish_ui)
    #
    #             completion_time = _ended - _started
    #             self.report.simple_title(f"Processing took: {completion_time:.4f}s")
    #     else:
    #         raise RuntimeError("Report never set. Cannot init processing thread.")
    #
    # def start_process(
    #     self,
    #     req: MTLRequest,
    #     ui: MTLUi,
    # ):
    #     """
    #     Starts the data processing functions.
    #     """
    #     if self.report is not None:
    #         self.reset_report(ui.stext)
    #
    #         if req.process_type == MTLProcessorType.DOWNLOAD:
    #             report_name = "downloading_mtl_from_mango"
    #         else:
    #             report_name = (
    #                 f"{req.process_type.value}_{req.data_table.lower()}_by_{req.report_name}"
    #                 if req.report_name is not None
    #                 else f"{req.process_type.value}_{req.data_table.lower()}"
    #             )
    #
    #         self.report.create_report(report_name)
    #     else:
    #         raise RuntimeError(
    #             "Report was never set, cannot start the processing functions."
    #         )
    #
    #     if (
    #         req.process_type == MTLProcessorType.NONE
    #         or req.env_types == MTLEnvironmentTypes.NONE
    #         and req.process_type != MTLProcessorType.DOWNLOAD
    #     ):
    #         self.app.after(
    #             0,
    #             lambda r=self.report: r.error(
    #                 "Please make sure your environment types are selected and to select"
    #                 " either the Compare or Append radio button.",
    #                 popup=True,
    #             ),
    #         )
    #         return
    #
    #     if self.process_thread and self.process_thread.is_alive():
    #         self.app.after(
    #             0,
    #             lambda r=self.report: r.warning(
    #                 "Process already running!",
    #                 popup=True,
    #             ),
    #         )
    #         return
    #
    #     ui.process_button.config(state=DISABLED)
    #
    #     ui.progress_bar.start()
    #
    #     self.process_thread = Thread(
    #         target=lambda: self._start_thread(req, ui),
    #         daemon=True,
    #     )
    #
    #     self.process_thread.start()
