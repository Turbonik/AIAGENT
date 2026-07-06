class Geometry:
    def distance(self, A, B):
        # Расстояние между двумя векторами A и B
        return ((A[0] - B[0])**2 + (A[1] - B[1])**2 + (A[2] - B[2])**2)**0.5

    def triangle_area(self, A, B, C):
        # Площадь треугольника с вершинами A, B и C
        return 0.5 * abs(A[0]*(B[1]-C[1]) + B[0]*(C[1]-A[1]) + C[0]*(A[1]-B[1]))

    def angle(self, A, B, C):
        # Угол между векторами A и B
        dot_product = A[0]*B[0] + A[1]*B[1] + A[2]*B[2]
        magnitude_A = (A[0]**2 + A[1]**2 + A[2]**2)**0.5
        magnitude_B = (B[0]**2 + B[1]**2 + B[2]**2)**0.5
        angle_rad = math.acos(dot_product / (magnitude_A * magnitude_B))
        return math.degrees(angle_rad)