from datetime import timedelta


class timedelta(timedelta):
    def to_string(
        self,
        hh_f: str = "02.0f",
        mm_f: str = "02.0f",
        ss_f: str = "02.0f",
        ms_f: str | None = "03.0f",
    ):
        """Convert timedelta to a string in HH:MM:SS(.sss) format."""
        mm, ss = divmod(self.total_seconds(), 60)
        hh, mm = divmod(mm, 60)
        s = f"{hh:{hh_f}}:{mm:{mm_f}}:{ss:{ss_f}}"
        if ms_f is not None:
            ms = self.microseconds / 1000 if self.microseconds else 0
            s = s + f".{ms:{ms_f}}"
        return s
