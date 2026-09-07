"""
Перечисления идентификаторов объектов глобального мира, не принадлежащих
ни одной расе: точки интереса Ничьей земли.
"""

from enum import Enum


class PointOfInterestId(str, Enum):
    """Идентификаторы мест Ничьей земли."""

    # Лорные ориентиры: существуют в единственном экземпляре
    RUSTY_SWORDS_VALLEY = "poi_rusty_swords_valley"
    RADIANCE_CRATER = "poi_radiance_crater"
    OLD_STADT = "poi_old_stadt"
    SORROW_LOWLAND = "poi_sorrow_lowland"
    SIEGE_COLOSSI_GRAVEYARD = "poi_siege_colossi_graveyard"

    # Процедурные места: генератор рассыпает их по нейтральным гексам
    ASH_GEYSERS = "poi_ash_geysers"
    GLASS_GROVES = "poi_glass_groves"
    BEAST_BARROWS = "poi_beast_barrows"
    MANUFACTORY_RUINS = "poi_manufactory_ruins"
