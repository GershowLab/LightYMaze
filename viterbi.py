import numpy as np

class Viterbi:
    _trans_prob:np.ndarray #tp[i,j] probability of transition from i to j
    def __init__(self, trans_prob):
        self._log_trans_prob = np.log(np.clip(trans_prob,1e-20, 1))
        self._tvalid = trans_prob > 0
        self._log_prob = []
        self._prev = []

    def new_obs(self, log_p_obs):
        if not self._log_prob:
            self._log_prob = [np.array(log_p_obs)]
            self._prev = [()]
        else:
            S = len(log_p_obs)
            last_log_prob = self._log_prob[-1]
            log_prob = last_log_prob-1e12
            prev = np.zeros_like(last_log_prob)
            for s in range(0,S):
                for r in range(0,S):
                    if self._tvalid[r,s]:
                        trial_prob = last_log_prob[r] +self._log_trans_prob[r,s]+log_p_obs[s]
                        if trial_prob > log_prob[s]:
                            log_prob[s] = trial_prob
                            prev[s] = r
            self._log_prob.append(log_prob)
            self._prev.append(prev)
        return np.argmax(self._log_prob[-1])

    def most_likely_path(self):
        T = len(self._log_prob)
        path = np.zeros((T,), dtype=int)
        path[-1] = np.argmax(self._log_prob[-1])
        for t in range(T - 2, -1, -1):
            path[t] = self._prev[t + 1][path[t + 1]]
        return path
    #pobs --> T time steps x S states; probability of each state given observation at time T
    #init_prob is S, initial state probability; if not given, observation probabilities are used
    # def decode(self, pobs:np.ndarray, init_prob:np.ndarray = None):
    #
    #     #convert to log, saturate at very low probabilities
    #
    #     tp = np.log(np.clip(self._trans_prob, 1e-12, 1))
    #     tvalid = self._trans_prob > 0
    #     pobs = np.log(np.clip(pobs, 1e-12, 1))
    #
    #     T,S = np.shape(pobs)
    #     prob = np.zeros((T,S)) - 1e12
    #     prev = np.zeros((T,S))
    #
    #     prob[0, :] = pobs[0, :]
    #
    #     if init_prob is None:
    #         init_prob = np.zeros(S)
    #
    #     prob[0, :] = init_prob + pobs[0, :]
    #
    #     #adapted from https://en.wikipedia.org/wiki/Viterbi_algorithm
    #     #changed to log probablity
    #
    #     for t in range(1,T):
    #         for s in range(0,S):
    #             for r in range(0,S):
    #                 if tvalid[r,s]:
    #                     trial_prob = prob[t-1,r]+tp[r,s]+pobs[t,s]
    #                     if trial_prob > prob[t,s]:
    #                         prob[t,s] = trial_prob
    #                         prev[t,s] = r
    #
    #     path = np.zeros((T,1),dtype=int)
    #     path[T-1] = np.argmax(prob[T-1,:])
    #     for t in range(T-2,-1,-1):
    #         path[t] = prev[t+1][path[t+1]]
    #     return path