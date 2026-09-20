"""Windows worker lifetime management using an unnamed, non-inheritable Job Object."""

import subprocess
from contextlib import suppress
from pathlib import Path


class WindowsJob:
    def __init__(self):
        import win32api
        import win32con
        import win32job

        self._api = win32api
        self._access = win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE
        self._jobs = win32job
        self._handle = win32job.CreateJobObject(None, None)
        try:
            limits = win32job.QueryInformationJobObject(
                self._handle, win32job.JobObjectExtendedLimitInformation
            )
            limits["BasicLimitInformation"]["LimitFlags"] = (
                win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            )
            win32job.SetInformationJobObject(
                self._handle, win32job.JobObjectExtendedLimitInformation, limits
            )
        except BaseException:
            self.close()
            raise

    def assign(self, pid):
        handle = self._api.OpenProcess(self._access, False, pid)
        try:
            self._jobs.AssignProcessToJobObject(self._handle, handle)
        finally:
            handle.Close()

    def close(self):
        if self._handle is not None:
            self._handle.Close()
            self._handle = None


def start_process(command, env):
    job = WindowsJob()
    process = None
    try:
        # The trusted bootstrap waits on stdin before importing the target module. No workload
        # can create descendants before assignment; EOF also exits if the host dies first.
        bootstrap = str(Path(__file__).with_name("worker_bootstrap.py"))
        process = subprocess.Popen(
            [command[0], bootstrap, *command[2:]],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        job.assign(process.pid)
        with process.stdin as gate:
            gate.write(b"\x01")
            gate.flush()
        return process, job
    except BaseException:
        try:
            job.close()
        finally:
            if process is not None:
                try:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=2)
                finally:
                    for stream in (process.stdin, process.stdout, process.stderr):
                        with suppress(OSError):
                            stream.close()
        raise
