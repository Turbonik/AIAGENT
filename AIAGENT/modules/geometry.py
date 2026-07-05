class Geometry:
    def distance(self, A, B):
        # Calculate the Euclidean distance between two points in 3D space
        return ((A[0] - B[0])**2 + (A[1] - B[1])**2 + (A[2] - B[2])**2)**0.5

    def triangle_area(self, A, B, C):
        # Calculate the area of a triangle given its vertices
        x1, y1, z1 = A
        x2, y2, z2 = B
        x3, y3, z3 = C
        
        # Using Heron's formula to calculate the area
        s = (self.distance(A, B) + self.distance(B, C) + self.distance(C, A)) / 2
        area = (s * (s - self.distance(A, B)) * (s - self.distance(B, C)) * (s - self.distance(C, A))) ** 0.5
        return area

    def angle(self, A, B, C):
        # Calculate the angle between two vectors in radians
        dot_product = self.dot(A, B)
        magnitude_A = self.length(A)
        magnitude_B = self.length(B)
        
        if magnitude_A == 0 or magnitude_B == 0:
            return 0
        
        cos_theta = dot_product / (magnitude_A * magnitude_B)
        theta = math.acos(cos_theta)
        return theta