import asyncio
import logging
from homeassistant.helpers.script import (
    Script,
    DATA_NEW_SCRIPT_RUNS_NOT_ALLOWED,
    SCRIPT_MODE_SINGLE,
    SCRIPT_MODE_RESTART,
    SCRIPT_MODE_QUEUED,
    _ScriptRun,
    _QueuedScriptRun,
    _VarsType,
    script_stack_cv,
)
from homeassistant.core import Context
from homeassistant import exceptions
from copy import copy
from homeassistant.util.dt import utcnow


from collections.abc import Callable
from typing import Any, cast
from homeassistant.helpers.trace import script_execution_set
from homeassistant.components.logger import LOGSEVERITY


class ObservableScript(Script):
    async def async_run(
        self,
        run_variables: _VarsType | None = None,
        context: Context | None = None,
        started_action: Callable[..., Any] | None = None,
    ) -> _ScriptRun | _QueuedScriptRun:
        """Run script."""
        if context is None:
            self._log(
                "Running script requires passing in a context", level=logging.WARNING
            )
            context = Context()

        # Prevent spawning new script runs when Home Assistant is shutting down
        if DATA_NEW_SCRIPT_RUNS_NOT_ALLOWED in self._hass.data:
            self._log("Home Assistant is shutting down, starting script blocked")
            return

        # Prevent spawning new script runs if not allowed by script mode
        if self.is_running:
            if self.script_mode == SCRIPT_MODE_SINGLE:
                if self._max_exceeded != "SILENT":
                    self._log("Already running", level=LOGSEVERITY[self._max_exceeded])
                script_execution_set("failed_single")
                return
            if self.script_mode != SCRIPT_MODE_RESTART and self.runs == self.max_runs:
                if self._max_exceeded != "SILENT":
                    self._log(
                        "Maximum number of runs exceeded",
                        level=LOGSEVERITY[self._max_exceeded],
                    )
                script_execution_set("failed_max_runs")
                return

        # If this is a top level Script then make a copy of the variables in case they
        # are read-only, but more importantly, so as not to leak any variables created
        # during the run back to the caller.
        if self.top_level:
            if self.variables:
                try:
                    variables = self.variables.async_render(
                        self._hass,
                        run_variables,
                    )
                except exceptions.TemplateError as err:
                    self._log("Error rendering variables: %s", err, level=logging.ERROR)
                    raise
            elif run_variables:
                variables = dict(run_variables)
            else:
                variables = {}

            variables["context"] = context
        else:
            if self._copy_variables_on_run:
                variables = cast(dict, copy(run_variables))
            else:
                variables = cast(dict, run_variables)

        # Prevent non-allowed recursive calls which will cause deadlocks when we try to
        # stop (restart) or wait for (queued) our own script run.
        script_stack = script_stack_cv.get()
        if (
            self.script_mode in (SCRIPT_MODE_RESTART, SCRIPT_MODE_QUEUED)
            and (script_stack := script_stack_cv.get()) is not None
            and id(self) in script_stack
        ):
            script_execution_set("disallowed_recursion_detected")
            self._log("Disallowed recursion detected", level=logging.WARNING)
            return

        if self.script_mode != SCRIPT_MODE_QUEUED:
            cls = _ScriptRun
        else:
            cls = _QueuedScriptRun
        run = cls(
            self._hass, self, cast(dict, variables), context, self._log_exceptions
        )
        self._runs.append(run)
        if self.script_mode == SCRIPT_MODE_RESTART:
            # When script mode is SCRIPT_MODE_RESTART, first add the new run and then
            # stop any other runs. If we stop other runs first, self.is_running will
            # return false after the other script runs were stopped until our task
            # resumes running.
            self._log("Restarting")
            await self.async_stop(update_state=False, spare=run)

        if started_action:
            self._hass.async_run_job(started_action)
        self.last_triggered = utcnow()
        self._changed()

        try:
            await asyncio.shield(run.async_run())
            return run
        except asyncio.CancelledError:
            await run.async_stop()
            self._changed()
            raise
