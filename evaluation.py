from math import sqrt


class Result:
    def __init__(
        self, tp: int, tn: int, overpermission: int, underpermission: int
    ):
        self.tp: int = tp
        self.tn: int = tn
        self._fp: int = overpermission
        self._fn: int = underpermission

    @property
    def fp(self) -> float:
        return self._fp

    @property
    def fn(self) -> float:
        return self._fn

    def precision(self) -> float:
        """How correct was generator out of allowed accesses."""
        return self.tp / (self.tp + self._fp)

    def sensitivity(self) -> float:
        """How correct was generator detecting which accesses should be allowed
        by reference.

        Also may be called hit rate."""
        return self.tp / (self.tp + self._fn)

    def tpr(self) -> float:
        return self.sensitivity()

    def f_beta_score(self, beta: float) -> float:
        precision = self.precision()
        recall = self.sensitivity()
        return (
            (1 + beta**2)
            * precision
            * recall
            / ((beta**2 * precision) + recall)
        )

    def f1(self):
        return self.f_beta_score(1)

    def f2(self):
        return self.f_beta_score(2)

    def fowlkes_mallows_index(self):
        return sqrt(self.precision() * self.sensitivity())

    def fm(self):
        return self.fowlkes_mallows_index()

    def jaccard_index(self):
        return self.tp / (self.tp + self._fn + self.fp)

    def specificity(self) -> float:
        return self.tn / (self.tn + self._fp)

    def tnr(self) -> float:
        return self.specificity()

    def balanced_precision(self) -> float:
        return (self.tpr() + self.tnr()) / 2

    def summary(self) -> str:
        return f'''hits={self.tp} correct denials={self.tn} overpermission={self._fp} underpermission={self.fn}
precision={self.precision():.3} sensitivity={self.sensitivity():.3}
f1={self.f1():.3} f2={self.f2():.3} fm={self.fm():.3} csi={self.jaccard_index():.3}'''

    @staticmethod
    def summary_csv_header() -> str:
        """Return header line for csv file."""
        return 'generalization,hits,correct denials,overpermission,underpermission,precision,sensitivity,f1,f2,fm,csi\n'

    def summary_csv_line(self, generalization: str) -> str:
        """Return summary as a csv line."""
        return f'{generalization},{self.tp},{self.tn},{self._fp},{self.fn},{self.precision():.4},{self.sensitivity():.4},{self.f1():.4},{self.f2():.4},{self.fm():.4},{self.jaccard_index():.4}\n'

    @staticmethod
    def summary_tabular_full_header() -> str:
        return r'''\begin{table}[htbp]
  \caption{}
  \label{tab:}
  \centering
  \begin{tabular}[h]{@{}lrrrrrrrrrr@{}}
    \toprule
    Generalization & TP & TN & FP & FN & PPV & SEN & \(F_1\) & \(F_2\) & FM & CSI \\
    \midrule
'''

    @staticmethod
    def summary_tabular_footer() -> str:
        return '''    \\bottomrule
  \\end{tabular}
\\end{table}\n'''

    def summary_tabular_full_line(self, generalization: str) -> str:
        """Return summary as a csv line."""
        return f'{generalization}\t&\t{self.tp}\t&\t{self.tn}\t&\t{self._fp}\t&\t{self.fn}\t&\t{self.precision():.4}\t&\t{self.sensitivity():.4}\t&\t{self.f1():.4}\t&\t{self.f2():.4}\t&\t{self.fm():.4}\t&\t{self.jaccard_index():.4} \\\\\n'

    @staticmethod
    def summary_tabular_short_header() -> str:
        return r'''\begin{table}[htbp]
  \caption{}
  \label{tab:}
  \centering
  \begin{tabular}[h]{@{}lrrr@{}}
    \toprule
    Generalization & SEN & PPV & \(F_2\) \\
    \midrule
'''

    def summary_tabular_short_line(self, generalization: str) -> str:
        """Return summary as a csv line."""
        return f'{generalization}\t&\t{self.sensitivity():.4}\t&\t{self.precision():.4}\t&\t{self.f2():.4} \\\\\n'

    def __repr__(self) -> str:
        return f'Result({self.tp}, {self.tn}, {self._fp}, {self._fn})'

    def __str__(self) -> str:
        return f'({self.tp}, {self.tn}, {self._fp}, {self._fn})'
