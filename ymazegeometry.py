from abc import abstractmethod

import numpy as np
import matplotlib.pyplot as plt
import os
import cv2
import glob
from enum import IntEnum

from affinecalculator import AffineCalculator


class YMazeGeometry:
    def __init__(self):
        self.y_mm = None
        self.x_mm = None
        self.origin = np.array([0, 0]) #x,y
        self.maze_spacing = 9  # mm
        self.maze_centers = np.array([[0, -2], [-1, -1], [1, -1], [2, 0], [0, 0], [-2, 0], [-1, 1], [1, 1], [0, 2]])
        self.channel_length = 1.818  # mm
        self.channel_width = 0.7 # mm
        self.circle_dia = 2.5  # mm
        self.circle_offset = 3.052  # mm - circle center?
        self.central_circle_dia = self.channel_width*1.55  # mm -- exclude overlapping channel regions
        self.im_size_px = np.array([1000, 1000]) #h,w
       # self.center_px = self.im_size_px[::-1] / 2.0 #x,y
        # self.rotation = 0  # radians
        # self.mm_per_px = 0.05
        self._maze_mask = None
        self._region_mask = None
        self._imspace_to_real_space = AffineCalculator()
        self.generate_coordinates()
        self._mazes = []
        self._setup_mazes()

        # TODO more general affine transformation
    def _setup_mazes(self):
        self._mazes = []
        for j in range(len(self.maze_centers)):
            self._mazes.append(YMazeFootprint(self, j+1))

    def calculate_affine(self, imspacepts, realpts):
        print ("calc affine: create calculator")
        self._imspace_to_real_space = AffineCalculator(imspacepts, realpts)
        print("calc affine: generate coordinates")
        self.generate_coordinates()

    def bounding_box(self):
        return(self.origin, self.origin + self.im_size_px)#self.center_px - self.im_size_px / 2, self.center_px + self.im_size_px / 2)

    def two_point_rotation_and_scaling(self, centerPoint, maze4Center):
        centerPoint = np.asarray(centerPoint)
        maze4Center = np.asarray(maze4Center)
        delta = maze4Center - centerPoint
        pt3 = centerPoint + np.array([-delta[1], delta[0]])
        mc = self.maze_spacing*2
        self.calculate_affine((centerPoint, maze4Center, pt3),
                              ([0,0], [mc,0],[0,mc]))


    def set_image_size(self, sz):
        self.im_size_px = np.array(sz)
        self.generate_coordinates()
    #     self.center_px = self.im_size_px[::-1] / 2.0
    #     self.generate_coordinates()

    def sub_image(self, x, y, w, h):
        self.im_size_px = np.array([h, w])
        self.origin = self.origin + np.array([x, y])
        self.generate_coordinates()
        self._region_mask = None
        self._maze_mask = None

    def clip_to_mazes(self, pad_px=5, size_multiple=32):
        bb = np.array([self._imspace_to_real_space.transform_rev(*m.bounding_box()) for m in self._mazes])
        x = bb[:,0,:].flatten()
        y = bb[:,1,:].flatten()
        x1 = np.min(x)
        y1 = np.min(y)
        x2 = np.max(x)
        y2 = np.max(y)
        cx = 0.5 * (x2 + x1)
        cy = 0.5 * (y2 + y1)
        w = x2 - x1
        h = y2 - y1
        w = np.clip(size_multiple * np.ceil((w + pad_px * 2) / size_multiple), 0, self.im_size_px[1]).astype(int)
        h = np.clip(size_multiple * np.ceil((h + pad_px * 2) / size_multiple), 0, self.im_size_px[0]).astype(int)
        x = np.max((0, np.round(cx - w / 2))).astype(int)
        y = np.max((0, np.round(cy - h / 2))).astype(int)

        self.sub_image(x, y, w, h)
        return x, y, w, h

    def pixel_axes(self):
        xa = np.arange(self.im_size_px[1]) + self.origin[0]
        ya = np.arange(self.im_size_px[0]) + self.origin[1]
        return xa, ya

    def pixel_grid(self):
        x, y = np.meshgrid(*self.pixel_axes())
        return x,y

    def generate_coordinates(self):
        x,y = self.pixel_grid()
        # c = np.cos(self.rotation)
        # s = np.sin(self.rotation)
        self.x_mm, self.y_mm = self._imspace_to_real_space.transform_fwd(x,y)
        #
        # self.x_mm = (c * x - s * y) * self.mm_per_px
        # self.y_mm = (s * x + c * y) * self.mm_per_px

    # from documentation
    # • Intersection: state 1
    # • Channel 1: state 2
    # • Channel 2: state 3
    # • Channel 3: state 4
    # • Circle 1: state 5
    # • Circle 2: state 6
    # • Circle 3: state 7
    def generate_region_mask(self, maze_index):
        mask = np.zeros_like(self.x_mm)
        ctr_mm = self.maze_centers[maze_index] * self.maze_spacing


        max_range = self.circle_offset + self.circle_dia/2
        x = self.x_mm - ctr_mm[0]
        y = self.y_mm - ctr_mm[1]
        inds = (np.abs(x) <= max_range) & (np.abs(y) <= max_range)
        x = x[inds]
        y = y[inds]

        m = mask[inds]
        for j in range(3):
            c = np.cos(2 * np.pi / 3 * j)
            s = np.sin(-2 * np.pi / 3 * j)
            xr = c * x - s * y
            yr = c * y + s * x
            channel = (xr >= 0) & (xr <= self.channel_length) & (np.abs(yr) <= self.channel_width/2)
            circle = (xr - self.circle_offset) ** 2 + yr ** 2 < (self.circle_dia / 2) ** 2
            m[channel] = j + 2
            m[circle] = j + 5

        state1 = x ** 2 + y ** 2 <= (self.central_circle_dia / 2) ** 2
        m[state1] = 1
        mask[inds] = m
        return mask

    # from documentation
    # • Intersection: state 1
    # • Channel 1: state 2
    # • Channel 2: state 3
    # • Channel 3: state 4
    # • Circle 1: state 5
    # • Circle 2: state 6
    # • Circle 3: state 7
    def generate_connectivity_matrix(self, transition_probability=0.01):
        c = np.zeros((8, 8))

        # intersection is connected to channels bidirectionally
        c[1, (2, 3, 4)] = 1
        c[(2, 3, 4), 1] = 1

        # channels are connected to circles bidirectionally
        for j in range(2, 5):
            c[j, j + 3] = 1
            c[j + 3, j] = 1

        c = transition_probability * c
        for j in range(8):
            c[j, j] = 1 - np.sum(c[j, :])
        return c

    def get_maze_mask(self):
        if self._region_mask is None:
            self.generate_maze_mask()
        return self._maze_mask, self._region_mask

    def generate_maze_mask(self):
        maze_mask = np.zeros_like(self.x_mm)
        region_mask = np.zeros_like(maze_mask)

        for m in self._mazes:
            m.label_mask(region_mask, maze_mask)
        #
        # for j in range(len(self.maze_centers)):
        #     rm = self.generate_region_mask(j)
        #     maze_mask[rm > 0] = j + 1
        #     region_mask[rm > 0] = rm[rm > 0]
        self._maze_mask = maze_mask
        self._region_mask = region_mask

    def calibrate_geometry_from_image(self, frame):

        points = []
        self.set_image_size(frame.shape)

        def click_event(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                print(f"Selected: ({x}, {y})")
                points.append(np.array([x, y]))

        winname = "Click Center Maze, then Right Maze, then other mazes"
        cv2.namedWindow(winname, cv2.WINDOW_KEEPRATIO)
        cv2.imshow(winname, frame)
        cv2.resizeWindow(winname, (960,720))
        cv2.setMouseCallback(winname, click_event)

        while len(points) < 9:
            if (cv2.waitKey(1) & 0xFF == ord('q')):
                break


        cv2.destroyWindow(winname)
#        cv2.destroyAllWindows()
#
#         centerPoint = points[0]
#         rightMazePoint = points[1]
#
#         self.two_point_rotation_and_scaling(centerPoint, rightMazePoint)
        print ("start multi point")
        self.multi_point_rotation_and_scaling(points)

    def multi_point_rotation_and_scaling(self, points):
        centerPoint = points[0]
        rightMazePoint = points[1]
        print ("start two point")
        self.two_point_rotation_and_scaling(centerPoint, rightMazePoint)
        print ("find matching points")
        mc = [self.maze_spacing * np.asarray(mc) for mc in self.maze_centers]
        dstpoints = []
        for p in points:
            p = self._imspace_to_real_space.transform_fwd(*p)
            d = (np.asarray(mc)[:,0] - p[0])**2 + (np.asarray(mc)[:,1] - p[1])**2
            dstpoints.append(mc[np.argmin(d)])
        print ("calculate affine")
        self.calculate_affine(points, dstpoints)

    def diagnostic_image(self, img):
        [mm, rm] = self.get_maze_mask()
        r = img.copy()
        b = img.copy()
        g = img.copy()

        # • Circle 1: state 5
        # • Circle 2: state 6
        # • Circle 3: state 7

        r[np.logical_and(rm > 0, rm < 6)] = 255 #maze 1 = red
        g[rm == 6] = 255 #maze 2 = green
        b[rm == 7] = 255 #maze 3 = blue
        img = cv2.merge((b, g, r))
        mc = [self.maze_spacing * np.asarray(mc) for mc in self.maze_centers]
        for i in range(len(mc)):
            loc = (np.array(self._imspace_to_real_space.transform_rev(*mc[i])) - self.origin).astype(int)
            cv2.putText(img, f"{i+1}", loc, cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 0), 4)
        return img
def calibrate_geometry_from_image(frame, ymg):
    ymg.calibrate_geometry_from_image(frame)


def split_tiff_folder_into_9(folder_path, ymg, fps=30):
    # Collect TIFF files (supports .tif and .tiff)
    tiff_files = sorted(
        glob.glob(os.path.join(folder_path, "*.tif")) +
        glob.glob(os.path.join(folder_path, "*.tiff"))
    )

    if len(tiff_files) == 0:
        raise ValueError("No TIFF files found in folder.")

    print(f"Found {len(tiff_files)} TIFF frames.")

    # Load first frame for mask sizing
    first_frame = cv2.imread(tiff_files[0])

    maze_mask, _ = ymg.generate_maze_mask()

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writers = []
    bounding_boxes = []

    # Precompute bounding boxes
    for i in range(9):
        mask = (maze_mask == i + 1)
        coords = np.column_stack(np.where(mask))
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        bounding_boxes.append((x_min, x_max, y_min, y_max))

        width = x_max - x_min
        height = y_max - y_min

        output_path = os.path.join(folder_path, f"maze_{i + 1}.mp4")
        writers.append(cv2.VideoWriter(output_path, fourcc, fps, (width, height)))

    print("Splitting TIFF sequence...")

    for file in tiff_files:
        frame = cv2.imread(file)
        if frame is None:
            continue  # skip unreadable frames
        for i in range(9):
            x_min, x_max, y_min, y_max = bounding_boxes[i]
            cropped = frame[y_min:y_max, x_min:x_max]
            writers[i].write(cropped)

    for w in writers:
        w.release()

    print("Finished. 9 maze videos saved in folder:", folder_path)


def main(folder_path):
    if not os.path.isdir(folder_path):
        raise FileNotFoundError("Provided path is not a folder.")

    # Collect TIFF files
    tiff_files = sorted(
        glob.glob(os.path.join(folder_path, "*.tif")) +
        glob.glob(os.path.join(folder_path, "*.tiff"))
    )

    if len(tiff_files) == 0:
        raise ValueError("No TIFF files found.")

    # Load first frame
    first_frame = cv2.imread(tiff_files[0])
    if first_frame is None:
        raise ValueError("Could not read first TIFF frame.")

    # ⚡ Adjust mask size to match actual frame size
    ymg = YMazeGeometry()
    frame_h, frame_w = first_frame.shape[:2]
    ymg.im_size_px = np.array([frame_w, frame_h])
    ymg.center_px = ymg.im_size_px / 2.0
    ymg.generate_coordinates()

    # Calibration
    calibrate_geometry_from_image(first_frame, ymg)

    # Split TIFF frames
    split_tiff_folder_into_9(folder_path, ymg)


class YMazeFootprint:
    def __init__(self, ymg, ID):
        self.ymg : YMazeGeometry = ymg
        self.shapes = []
        self.ID = ID
        self.center = ymg.maze_spacing*np.asarray(ymg.maze_centers[ID-1]).astype(np.float32)
        self.populate_shapes()

    def populate_shapes(self):
        dy = self.ymg.channel_width/2
        dx = self.ymg.channel_length
        vertices = np.array(((0, -dy), (dx, -dy), (dx, dy), (0,dy))).astype(np.float32)
        circle_center = np.array((self.ymg.circle_offset,0)).astype(np.float32)
        self.shapes = []
        for j in range(3):
            c = np.cos(2 * np.pi / 3 * j)
            s = np.sin(-2 * np.pi / 3 * j)
            r = np.array(((c, s), (-s, c))).astype(np.float32)
            self.shapes.append(Polygon(j+2,vertices@r + self.center))
            self.shapes.append(Circle(j+5, circle_center@r + self.center, self.ymg.circle_dia/2))
        self.shapes.append(Circle(1, self.center, self.ymg.central_circle_dia/2))

    def label_mask(self, region_mask, maze_mask, label = None):
       if label is None:
           label = self.ID
       for s in self.shapes:
           inds = s.label_mask(region_mask, self.ymg)
           maze_mask[inds] = label

    def bounding_box(self):
        bb = np.array([s.bounding_box() for s in self.shapes])
        x = bb[:,0,:].flatten()
        y = bb[:,1,:].flatten()
        minx = np.min(x)
        miny = np.min(y)
        maxx = np.max(x)
        maxy = np.max(y)
        return (minx,maxx,maxx,minx),(miny, miny, maxy, maxy)




class Shape:
    def __init__(self, ID):
        self.ID = ID
    @abstractmethod
    def interior(self,x,y):
        pass
    @abstractmethod
    def bounding_box(self):
        pass #xlist, ylist

    def find_interior(self, ymg: YMazeGeometry):
        #finds points in x_mm, y_mm that are internal to the shape
        xc,yc = self.bounding_box()
        xc,yc = ymg._imspace_to_real_space.transform_rev(xc,yc)
        minx = np.min(xc)
        maxx = np.max(xc)
        miny = np.min(yc)
        maxy = np.max(yc)
        xa,ya = ymg.pixel_axes()
        xi = np.nonzero(np.logical_and(minx <= xa, xa <= maxx))[0]
        yi = np.nonzero(np.logical_and(miny <= ya, ya <= maxy))[0]
        inds = np.ix_(yi,xi)
        valid = self.interior(ymg.x_mm[inds], ymg.y_mm[inds])
        j,i = np.meshgrid(xi,yi)
        return (i[valid], j[valid])

    def label_mask(self, mask, ymg, label = None):
        if label is None:
            label = self.ID
        inds = self.find_interior(ymg)
        mask[inds] = label
        return inds

class Polygon(Shape):
    def __init__(self, ID, vertices):
        super().__init__(ID)
        self.vertices = vertices

    def interior(self,x,y):
        xx = np.asarray(x).flatten()
        yy = np.asarray(y).flatten()
        interior = np.array([self.interior_point(pt) for pt in zip(xx, yy)])
        return interior.reshape(x.shape)

    def bounding_box(self):
        v = np.asarray(self.vertices).astype(np.float32)
        minx = np.min(v[:,0])
        maxx = np.max(v[:,0])
        miny = np.min(v[:,1])
        maxy = np.max(v[:,1])
        return (minx,maxx,maxx,minx),(miny, miny, maxy, maxy)

    def interior_point(self, point):
        """
        Checks if a point (2-element array) is inside a convex polygon (N, 2 array)
        using the cross-product (same-side) method.
        Vertices must be in consistent order (CW or CCW).
        adapted from google search ai generated code
        """
        # Ensure points are numpy arrays
        point = np.asarray(point)
        vertices = np.asarray(self.vertices)

        # Check if point is on the same side of all edges
        num_vertices = len(vertices)
        # Calculate initial cross product sign
        v1 = vertices[-1] - vertices[0]  # Last vertex to first vertex
        v2 = point - vertices[0]
        # Use 2D cross product proxy: u[0]*v[1] - u[1]*v[0]
        initial_sign = np.sign(v1[0] * v2[1] - v1[1] * v2[0])

        for i in range(num_vertices):
            v1 = vertices[i] - vertices[(i + 1) % num_vertices]  # Edge vector
            v2 = point - vertices[(i + 1) % num_vertices]  # Point vector relative to end of edge

            current_sign = np.sign(v1[0] * v2[1] - v1[1] * v2[0])

            # If the sign changes, the point is outside.
            # Points on the boundary (sign == 0) can be considered inside or outside based on needs.
            if current_sign != initial_sign and current_sign != 0:
                return False
        return True
class Circle(Shape):
    def __init__(self, ID, center, radius):
        super().__init__(ID)
        self.center = np.asarray(center).flatten()
        self.radius = radius

    def interior(self,x,y):
        xx = np.asarray(x).flatten()
        yy = np.asarray(y).flatten()
        interior = (xx - self.center[0])**2 + (yy - self.center[1])**2 <= self.radius**2
        return interior.reshape(x.shape)

    def bounding_box(self):
        return (self.center[0] + self.radius*np.array((-1,1,1,-1))).astype(np.float32), (self.center[1] + self.radius*np.array((-1,-1,1,1))).astype(np.float32)
# from documentation
# • Intersection: state 1
# • Channel 1: state 2
# • Channel 2: state 3
# • Channel 3: state 4
# • Circle 1: state 5
# • Circle 2: state 6
# • Circle 3: state 7
class MazePart(IntEnum):
    INTERSECTION = 1
    CHANNEL1 = 2
    CHANNEL2 = 3
    CHANNEL3 = 4
    CIRCLE1 = 5
    CIRCLE2 = 6
    CIRCLE3 = 7

    @staticmethod
    def all_parts():
        return [MazePart(i) for i in range(1, 8)]


class Region:
    def __init__(self, part: MazePart, region_map: np.ndarray = None):
        self.part = part
        self.loc = np.array((0, 0))
        self.cov = np.eye(2)
        self.det_cov = np.linalg.det(self.cov)
        self.icov = np.linalg.inv(self.cov)
        self.set_region_stats(region_map)

    def set_region_stats(self, region_map: np.ndarray):
        if region_map is None:
            return
        [x, y] = np.meshgrid(np.arange(region_map.shape[1]), np.arange(region_map.shape[0]))
        xv = x[region_map == self.part]
        yv = y[region_map == self.part]
        self.loc = np.array((np.mean(xv), np.mean(yv)))
        self.cov = np.cov((xv, yv))
        self.det_cov = np.linalg.det(self.cov)
        self.icov = np.linalg.inv(self.cov)

    def distance(self, loc):
        return np.linalg.norm(self.loc - np.asarray(loc))

    def logP(self, loc):
        dx = np.asarray(loc) - self.loc
        logP = -0.5 * (dx @ self.icov @ dx + np.log(self.det_cov))  # TODO this formula is wrong
        return logP

    @staticmethod
    def all_regions(region_map: np.ndarray):
        return [Region(r, region_map) for r in MazePart.all_parts()]

    @staticmethod
    def log_prob_region_list(loc, region_list):
        log_prob = [r.logP(loc) for r in region_list]
        return log_prob, region_list[np.argmax(log_prob)].part


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python3 ymazegeometry.py /path/to/tiff_folder")
    else:
        main(sys.argv[1])


def marctest():
    ymg = YMazeGeometry()
    print(ymg.generate_connectivity_matrix())
    [mm, rm] = ymg.get_maze_mask()
    plt.figure(1)
    plt.imshow(mm)
    plt.show(block=False)
    plt.figure(2)
    plt.imshow(rm)
    plt.show(block=True)
    print("test finished")

# marctest()

# from documentation
# • Intersection: state 1
# • Channel 1: state 2
# • Channel 2: state 3
# • Channel 3: state 4
# • Circle 1: state 5
# • Circle 2: state 6
# • Circle 3: state 7
