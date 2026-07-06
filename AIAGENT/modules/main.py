# main.py
from geometry import Geometry
from vector import Vector

def main():
    # Создаем объекты классов
    point1 = Vector(1, 2, 3)
    point2 = Vector(4, 5, 6)

    # Вызываем методы классов
    distance = Geometry.distance(point1, point2)
    area = Geometry.triangle_area(point1, point2, Vector(0, 0, 0))
    angle = Geometry.angle(point1, point2, Vector(0, 0, 0))

    # Выводим результаты
    print(f"Distance: {distance}")
    print(f"Area: {area}")
    print(f"Angle: {angle}")

if __name__ == "__main__":
    main()