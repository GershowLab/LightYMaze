import time

import numpy as np


class TrainingProtocol:
    def __init__(self):
        self._t0 = time.monotonic()
        self._finished = False
        pass

    def led_value_and_update(self, t = None):
        return (0,0,0), False

    def start(self, t = None):
        if t is None:
            self._t0 = time.monotonic()
        else:
            self._t0 = t

    def finished(self, t = None):
        return self._finished

class TimeRangeAndValue:
    def __init__(self, trange, value):
        self.trange = trange
        self.value = value

    def in_range(self, t, period = None):
        return TimeRangeAndValue.in_time_interval(t, self.trange, period)
        # if period is not None:
        #     t = t % period
        #     if self.trange[0] > self.trange[1]:
        #         return t >= self.trange[1] or t < self.trange[0]
        # return self.trange[0] <= t < self.trange[1]

    @staticmethod
    def in_time_interval(t, trange, period = None):
        if period is not None:
            t = t % period
        else:
            t = t
            if trange[0] > trange[1]:
                return t >= trange[1] or t < trange[0]
        return trange[0] <= t < trange[1]


class TemporalTrainingProtocol(TrainingProtocol):
    def __init__(self, period, time_ranges_and_values, duration):
        super().__init__()
        self.period = period
        self.time_ranges_and_values = time_ranges_and_values
        self.duration = duration


    def led_value_and_update(self, t = None):
        if t is None:
            t = time.monotonic()
        for tr in self.time_ranges_and_values:
            if tr.in_range(t - self._t0, self.period):
                return tr.value, True

        return None, False

    def finished(self, t = None):
        if t is None:
            t = time.monotonic()
        self._finished = t - self._t0 > self.duration

    @staticmethod
    def associative_protocol(period = 30, n_reps = 20, cs_rgbpct = (0, 0, 25), us_rgbpct = (255, 0, 0), cs_tr = (0, 15), us_tr = (0, 15)):
        duration = period * n_reps
        tedge = np.sort(np.unique(np.concatenate((us_tr, cs_tr, (0,period)))))
        tre = []
        for j in range(len(tedge)-1):
            if TimeRangeAndValue.in_time_interval(tedge[j], cs_tr):
                if TimeRangeAndValue.in_time_interval(tedge[j], us_tr):
                    val = np.maximum(cs_rgbpct, us_rgbpct)
                else:
                    val = cs_rgbpct
            else:
                if TimeRangeAndValue.in_time_interval(tedge[j], us_tr):
                    val = us_rgbpct
                else:
                    val = (0,0,0)
            tre.append(TimeRangeAndValue((tedge[j], tedge[j+1]), val))
        return TemporalTrainingProtocol(period, tre, duration)

    @staticmethod
    def standard_paired_protocol(period = 30, n_reps = 20, cs_rgbpct = (0, 0, 25), us_rgbpct = (255, 0, 0), cs_tr = (0, 15), us_tr = (0, 15)):
        return TemporalTrainingProtocol.associative_protocol(period, n_reps, cs_rgbpct, us_rgbpct, cs_tr, us_tr)

    @staticmethod
    def standard_unpaired_protocol(period=30, n_reps=20, cs_rgbpct=(0, 0, 25), us_rgbpct=(255, 0, 0), cs_tr=(0, 15),
                                 us_tr=(15, 30)):
        return TemporalTrainingProtocol.associative_protocol(period, n_reps, cs_rgbpct, us_rgbpct, cs_tr, us_tr)

if __name__ == "__main__":
    ttp = TemporalTrainingProtocol.standard_paired_protocol()
    for t in range(0, 100):
        val,update = ttp.led_value_and_update(t)
        print(f"{t}: val: {val}, update: {update}")

