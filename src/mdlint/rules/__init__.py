from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mdlint.rules.base import Rule

from mdlint.rules.md001 import MD001
from mdlint.rules.md003 import MD003
from mdlint.rules.md004 import MD004
from mdlint.rules.md005 import MD005
from mdlint.rules.md007 import MD007
from mdlint.rules.md009 import MD009
from mdlint.rules.md010 import MD010
from mdlint.rules.md011 import MD011
from mdlint.rules.md012 import MD012
from mdlint.rules.md013 import MD013
from mdlint.rules.md014 import MD014
from mdlint.rules.md018 import MD018
from mdlint.rules.md019 import MD019
from mdlint.rules.md020 import MD020
from mdlint.rules.md021 import MD021
from mdlint.rules.md022 import MD022
from mdlint.rules.md023 import MD023
from mdlint.rules.md024 import MD024
from mdlint.rules.md025 import MD025
from mdlint.rules.md026 import MD026
from mdlint.rules.md027 import MD027
from mdlint.rules.md028 import MD028
from mdlint.rules.md029 import MD029
from mdlint.rules.md030 import MD030
from mdlint.rules.md031 import MD031
from mdlint.rules.md032 import MD032
from mdlint.rules.md033 import MD033
from mdlint.rules.md034 import MD034
from mdlint.rules.md035 import MD035
from mdlint.rules.md036 import MD036
from mdlint.rules.md037 import MD037
from mdlint.rules.md038 import MD038
from mdlint.rules.md039 import MD039
from mdlint.rules.md040 import MD040
from mdlint.rules.md041 import MD041
from mdlint.rules.md042 import MD042
from mdlint.rules.md043 import MD043
from mdlint.rules.md044 import MD044
from mdlint.rules.md045 import MD045
from mdlint.rules.md046 import MD046
from mdlint.rules.md047 import MD047
from mdlint.rules.md048 import MD048
from mdlint.rules.md049 import MD049
from mdlint.rules.md050 import MD050
from mdlint.rules.md051 import MD051
from mdlint.rules.md052 import MD052
from mdlint.rules.md053 import MD053
from mdlint.rules.md054 import MD054
from mdlint.rules.md055 import MD055
from mdlint.rules.md056 import MD056
from mdlint.rules.md058 import MD058
from mdlint.rules.md059 import MD059
from mdlint.rules.md060 import MD060

__all__ = ["RULE_REGISTRY"]

RULE_REGISTRY: dict[str, type[Rule]] = {
    "MD001": MD001,
    "MD003": MD003,
    "MD004": MD004,
    "MD005": MD005,
    "MD007": MD007,
    "MD009": MD009,
    "MD010": MD010,
    "MD011": MD011,
    "MD012": MD012,
    "MD013": MD013,
    "MD014": MD014,
    "MD018": MD018,
    "MD019": MD019,
    "MD020": MD020,
    "MD021": MD021,
    "MD022": MD022,
    "MD023": MD023,
    "MD024": MD024,
    "MD025": MD025,
    "MD026": MD026,
    "MD027": MD027,
    "MD028": MD028,
    "MD029": MD029,
    "MD030": MD030,
    "MD031": MD031,
    "MD032": MD032,
    "MD033": MD033,
    "MD034": MD034,
    "MD035": MD035,
    "MD036": MD036,
    "MD037": MD037,
    "MD038": MD038,
    "MD039": MD039,
    "MD040": MD040,
    "MD041": MD041,
    "MD042": MD042,
    "MD043": MD043,
    "MD044": MD044,
    "MD045": MD045,
    "MD046": MD046,
    "MD047": MD047,
    "MD048": MD048,
    "MD049": MD049,
    "MD050": MD050,
    "MD051": MD051,
    "MD052": MD052,
    "MD053": MD053,
    "MD054": MD054,
    "MD055": MD055,
    "MD056": MD056,
    "MD058": MD058,
    "MD059": MD059,
    "MD060": MD060,
}
