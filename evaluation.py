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
precision={self.precision():.2} sensitivity={self.sensitivity():.2}
f1={self.f1():.2} f2={self.f2():.2} fm={self.fm():.2} csi={self.jaccard_index():.2}'''

    def __repr__(self) -> str:
        return f'Result({self.tp}, {self.tn}, {self._fp}, {self._fn})'

    def __str__(self) -> str:
        return f'({self.tp}, {self.tn}, {self._fp}, {self._fn})'
