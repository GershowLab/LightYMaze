import numpy as np
import matplotlib.pyplot as plt

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
        self.im_size_px = np.array([800,800])
        self.center_px = self.im_size_px/2.0
        self.rotation = 0 #radians
        self.mm_per_px = 0.05
        self.generate_coordinates()
        #TODO more general affine transformation

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
            mask[channel] = j + 1
            mask[circle] = j + 4
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

marctest()

#from documentation
#• Intersection: state 1
#• Channel 1: state 2
#• Channel 2: state 3
#• Channel 3: state 4
#• Circle 1: state 5
#• Circle 2: state 6
#• Circle 3: state 7