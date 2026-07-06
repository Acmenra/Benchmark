import logging
from enum import Enum, EnumType


logger = logging.getLogger(__name__)



class Coco(Enum):
    person = 0
    bicycle = 1
    car = 2
    motorcycle = 3
    airplane = 4
    bus = 5
    train = 6
    truck = 7
    boat = 8
    traffic_light = 9
    fire_hydrant = 10
    stop_sign = 11
    parking_meter = 12
    bench = 13
    bird = 14
    cat = 15
    dog = 16
    horse = 17
    sheep = 18
    cow = 19
    elephant = 20
    bear = 21
    zebra = 22
    giraffe = 23
    backpack = 24
    umbrella = 25
    handbag = 26
    tie = 27
    suitcase = 28
    frisbee = 29
    skis = 30
    snowboard = 31
    sports_ball = 32
    kite = 33
    baseball_bat = 34
    baseball_glove = 35
    skateboard = 36
    surfboard = 37
    tennis_racket = 38
    bottle = 39
    wine_glass = 40
    cup = 41
    fork = 42
    knife = 43
    spoon = 44
    bowl = 45
    banana = 46
    apple = 47
    sandwich = 48
    orange = 49
    broccoli = 50
    carrot = 51
    hot_dog = 52
    pizza = 53
    donut = 54
    cake = 55
    chair = 56
    couch = 57
    potted_plant = 58
    bed = 59
    dining_table = 60
    toilet = 61
    tv = 62
    laptop = 63
    mouse = 64
    remote = 65
    keyboard = 66
    cell_phone = 67
    microwave = 68
    oven = 69
    toaster = 70
    sink = 71
    refrigerator = 72
    book = 73
    clock = 74
    vase = 75
    scissors = 76
    teddy_bear = 77
    hair_drier = 78
    toothbrush = 79

    @classmethod
    def has_value(cls, value: int) -> bool:
        """Check if a given integer is a valid class ID."""
        return value in cls._value2member_map_

    @classmethod
    def name_of(cls, value: int) -> str:
        """Get class name by integer value."""
        if not cls.has_value(value):
            raise ValueError(f"Class ID {value} is not in COCO 2017 dataset.")
        return cls(value).name.replace('_', ' ').title()

    @classmethod
    def to_dict(cls) -> dict:
        """Convert enum to dictionary {id: 'name'}."""
        return {member.value: member.name.replace('_', ' ').title() for member in cls}