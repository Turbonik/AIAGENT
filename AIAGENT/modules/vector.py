import math

class Vector:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def length(self):
        # Длина вектора
        return (self.x**2 + self.y**2 + self.z**2)**0.5

    def normalize(self):
        # Нормализация вектора
        magnitude = self.length()
        if magnitude != 0:
            self.x /= magnitude
            self.y /= magnitude
            self.z /= magnitude

    def dot(self, other):
        # Скалярное произведение двух векторов
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other):
        # Векторное произведение двух векторов
        return Vector(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )