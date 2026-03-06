import numpy as np
import matplotlib.pyplot as plt
import os
import cv2
import glob

class YMazeGeometry:
    def __init__(self):
        self.y_mm = None
        self.x_mm = None
        self.maze_spacing = 9 #mm
        self.maze_centers = np.array([[0,2], [-1,1],[1,1], [2,0],[0,0],[-2,0],[-1,-1],[1,-1],[0,-2]])
        self.channel_length = 1.818 #mm
        self.channel_width = 0.4 #mm
        self.circle_dia = 2.5 #mm
        self.circle_offset = 3.052 #mm
        self.central_circle_dia = .462 #mm -- exclude overlapping channel regions
        self.im_size_px = np.array([1000,1000])
        self.center_px = self.im_size_px/2.0
        self.rotation = 0 #radians
        self.mm_per_px = 0.05
        self.generate_coordinates()
        #TODO more general affine transformation

    def two_point_rotation_and_scaling(self, centerPoint, maze4Center):
        self.center_px = centerPoint
        distmm = np.linalg.norm(self.maze_centers[3])*self.maze_spacing
        delta_px = maze4Center-centerPoint
        distpx = np.linalg.norm(delta_px)
        self.mm_per_px = distmm/distpx
        #this is hacky based on knowing maze4 is horizontally offset
        self.rotation = np.arctan2(-delta_px[1], delta_px[0])


    def generate_coordinates(self):
        x,y = np.meshgrid(np.arange(self.im_size_px[0])-self.center_px[0], np.arange(self.im_size_px[1])-self.center_px[1])
        c = np.cos(self.rotation)
        s = np.sin(self.rotation)

        self.x_mm = (c*x - s*y)*self.mm_per_px
        self.y_mm = (s*x + c*y)*self.mm_per_px

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
        ctr_mm = self.maze_centers[maze_index]*self.maze_spacing
        #reference geometry to maze center
        x = self.x_mm - ctr_mm[0]
        y = self.y_mm - ctr_mm[1]
        for j in range(3):
            c = np.cos(2*np.pi/3 * j)
            s = np.sin(2*np.pi/3*j)
            xr = c*x - s*y
            yr = c*y + s*x
            channel = (xr >= 0) & (xr <= self.channel_length) & (np.abs(yr) <= self.channel_width);
            circle = (xr - self.circle_offset)**2 + yr**2 < (self.circle_dia/2)**2
            mask[channel] = j + 2
            mask[circle] = j + 5
        state1 = x**2 + y**2 <= (self.central_circle_dia/2)**2
        mask[state1] = 1
        return mask
    def generate_maze_mask(self):
        maze_mask = np.zeros_like(self.x_mm)
        regionmask = np.zeros_like(maze_mask);
        for j in range(len(self.maze_centers)):
            rm = self.generate_region_mask(j)
            maze_mask[rm>0] = j+1
            regionmask[rm>0] = rm[rm>0]
        return maze_mask, regionmask

    def calibrate_geometry_from_image(self, frame):

        points = []

        def click_event(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                print(f"Selected: ({x}, {y})")
                points.append(np.array([x, y]))

        cv2.namedWindow("Click Center Maze, then Right Maze", cv2.WINDOW_KEEPRATIO)
        cv2.imshow("Click Center Maze, then Right Maze", frame)
        cv2.setMouseCallback("Click Center Maze, then Right Maze", click_event)

        while len(points) < 2:
            cv2.waitKey(1)

        cv2.destroyAllWindows()

        centerPoint = points[0]
        rightMazePoint = points[1]

        self.two_point_rotation_and_scaling(centerPoint, rightMazePoint)
        self.generate_coordinates()

        [mm, rm] = self.generate_maze_mask()
        plt.imshow(frame)
        plt.contour(mm)
        print("Calibration complete.")
        plt.show()


def calibrate_geometry_from_image(frame, ymg):
    ymg.calibrate_geometry_from_image(frame)
    #
    # points = []
    #
    # def click_event(event, x, y, flags, param):
    #     if event == cv2.EVENT_LBUTTONDOWN:
    #         print(f"Selected: ({x}, {y})")
    #         points.append(np.array([x, y]))
    #
    # cv2.imshow("Click Center Maze, then Right Maze", frame)
    # cv2.setMouseCallback("Click Center Maze, then Right Maze", click_event)
    #
    # while len(points) < 2:
    #     cv2.waitKey(1)
    #
    # cv2.destroyAllWindows()
    #
    # centerPoint = points[0]
    # rightMazePoint = points[1]
    #
    # ymg.two_point_rotation_and_scaling(centerPoint, rightMazePoint)
    # ymg.generate_coordinates()
    #
    # [mm,rm] = ymg.generate_maze_mask()
    # plt.imshow(frame)
    # plt.contour(mm)
    # print("Calibration complete.")
    # plt.show()

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

        output_path = os.path.join(folder_path, f"maze_{i+1}.mp4")
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

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python3 ymazegeometry.py /path/to/tiff_folder")
    else:
        main(sys.argv[1])

def marctest():
    ymg = YMazeGeometry()
    [mm,rm] = ymg.generate_maze_mask()
    plt.figure(1)
    plt.imshow(mm)
    plt.show(block=False)
    plt.figure(2)
    plt.imshow(rm)
    plt.show(block=True)
    print("test finished")




#marctest()

#from documentation
#• Intersection: state 1
#• Channel 1: state 2
#• Channel 2: state 3
#• Channel 3: state 4
#• Circle 1: state 5
#• Circle 2: state 6
#• Circle 3: state 7