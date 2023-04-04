class Result:
    def __init__(self, tp, tn, overpermission, underpermission):
        self.tp = tp
        self.tn = tn
        self._fp = overpermission
        self._fn = underpermission

    @property
    def fp(self):
        return self._fp

    @property
    def fn(self):
        return self._fn

    def precision(self):
        return self.tp / (self.tp + self._fp)

    def sensitivity(self):
        return self.tp / (self.tp + self._fn)

    def tpr(self):
        self.sensitivity()

    def specificity(self):
        return self.tn / (self.tn + self._fp)

    def tnr(self):
        self.specificity()

    def balanced_precision(self):
        return (self.tpr() + self.tnr()) / 2

    def summary(self):
        return f'''hits={self.tp} correct denials={self.tn} overpermission={self._fp} underpermission={self.fn}
precision={self.precision()} sensitivity={self.sensitivity()}
balanced precision={self.balanced_precision()}'''

    def __repr__(self):
        return f'Result({self.tp}, {self.tn}, {self._fp}, {self._fn})'

    def __str__(self):
        return f'({self.tp}, {self.tn}, {self._fp}, {self._fn})'
