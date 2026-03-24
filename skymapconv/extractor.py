import astropy.units as u
import cartopy.crs as ccrs
import matplotlib.image as mpl_image
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord


class Extractor():
    """Tool for digitising a raster image of a sky map projection. This is
    achieved using Matplotlib's coordinate transformation tools.
    This class creates an Axes which must be set to the same type of sky map
    projection as the source image and exactly aligned with the source image
    on a Figure canvas. Then, the coordinates of each pixel in the source image
    are converted into an astropy SkyCoord, which can be associated with the
    colour of that pixel in the source image.
    """

    def __init__(self, filepath: str, dpi: int = 100):
        self.filepath = filepath

        self.colours = mpl_image.imread(self.filepath)
        self.res_h,self.res_w,_ = self.colours.shape

        # PNG reads in as float from 0–1, everything else reads as int from 0–255
        # We need it to be 0–1 for use with matplotlib later
        if 'int' in str(self.colours.dtype):
            self.colours = self.colours/255

        # meshgrid of pixel coordinates (note inversion of y-axis by imread convention)
        ix = list(range(self.res_w))
        iy = list(reversed(range(self.res_h)))
        vx,vy = np.meshgrid(ix,iy)
        self.xy_pixels = np.vstack([vx.flatten(),vy.flatten()]).T

        # Request the figure to be a roughly reasonable size, but the display
        # backend may resize it anyway
        self.fig = plt.figure(dpi = dpi, num = "Input")
        self.fig.set_size_inches(self.res_w/dpi, self.res_h/dpi)

        # Place source image in background
        self.bg = self.fig.add_axes((0, 0, 1, 1), zorder = -1)
        self.bg.spines[:].set_visible(False)
        self.bg.get_xaxis().set_visible(False)
        self.bg.get_yaxis().set_visible(False)
        self.bg.imshow(self.colours)

        self._projection = 'Hammer'
        self._central_longitude = 0

        self.axes = None
        self.update_position(0.5, 0.5, 0.7)
        self._rebuild_axes()

    @property
    def projection(self):
        """The coordinate projection used in the source image as a string. Can
        be any projection from the list at
        https://cartopy.readthedocs.io/stable/reference/projections.html"""
        return self._projection

    @projection.setter
    def projection(self, new_proj: str):
        curr_proj = self._projection
        if new_proj != curr_proj:
            try:
                self._projection = new_proj
                self._rebuild_axes()
            except Exception:
                print("Updating projection failed")
                self._projection = curr_proj

    @property
    def central_longitude(self):
        """The central_longitude of the source projection in degrees."""
        return self._central_longitude

    @central_longitude.setter
    def central_longitude(self, new_clon: float):
        curr_clon = self._central_longitude
        if new_clon != curr_clon:
            try:
                self._central_longitude = new_clon
                self._rebuild_axes()
            except Exception:
                print("Updating central longitude failed")
                self._central_longitude = curr_clon

    def draw_idle(self):
        self.fig.canvas.draw_idle()

    def update_position(self, xmid: float = None, ymid: float = None, width: float = None):
        """Set the location and size of the sky map projection in the source image,
        as fractions of the width and height of the canvas. Set xmid and ymid
        to the middle of the sky map projection in the source image, and set
        width to the width of the projection. Because projections have a fixed
        aspect ratio, the height does not need to be set."""
        if xmid is not None:
            self.xmid = xmid
        if ymid is not None:
            self.ymid = ymid
        if width is not None:
            self.width = width
        if self.axes is not None:
            self.axes.set_position(self._axes_pos())
            self.draw_idle()

    def _axes_pos(self) -> tuple[float, float, float, float]:
        """Return a Matplotlib representation of the coordinate Axes position"""
        # Keep height constant because the fixed aspect ratio of each projection
        # means it isn't particuarly important. We could use 1, but in some
        # papers using equatorial coordinates the top and bottom of a
        # projection can be cropped out, meaning we need to allow projection
        # height to be greater than the canvas height. Use 2 for now
        height = 2.0
        xlow = self.xmid - self.width/2
        ylow = self.ymid - height/2
        return (xlow, ylow, self.width, height)

    def _rebuild_axes(self):
        proj_class = getattr(ccrs, self.projection)
        proj = proj_class(central_longitude = self.central_longitude)

        new_axes = self.fig.add_axes(self._axes_pos(), projection = proj)
        if self.axes is not None:
            self.axes.remove()
        self.axes = new_axes

        new_axes.axes.patch.set_visible(False) # Hide the white fill within the ellipse
        new_axes.set_global() # Full projection axes extent
        new_axes.set_xlim(new_axes.properties()['xlim'][::-1]) # Reverse for sky map
        # Add gridlines
        new_axes.gridlines(draw_labels = True, formatter_kwargs = dict(direction_label = False))

        self.draw_idle()

    def get_data(self, coord_frame: str, ignore_white: bool = True) -> tuple[SkyCoord, list]:
        """coord_frame should be the frame of the source image, likely one of
        'icrs', 'galactic', or 'supergalactic'.

        Set ignore_white to True to skip the transformation of any source pixels
        that are white (recommended to cut down on processing time).

        Returns a SkyCoord of all the data points successfully digitised, and an
        accompanying list of colours that has the same length.

        Read
        https://matplotlib.org/stable/users/explain/artists/transforms_tutorial.html
        to understand why this works. cartopy's Geodetic yields the appropriate
        transformation.
        """
        # Get display coordinates of the bg image (affected by fig size, DPI, etc)
        xy_display = self.bg.transData.transform(self.xy_pixels)

        # Get data-to-display coordinate transformation with current axes position/scale
        transData = ccrs.Geodetic()._as_mpl_transform(axes = self.axes)

        # Convert each pixel position to data coordinates
        xy_data = transData.inverted().transform(xy_display)

        pix_0 = self.colours[0,0]
        c_white = np.ones(shape = pix_0.shape, dtype = pix_0.dtype)

        # Build properties of "valid" pixels
        valid_x,valid_y,valid_col = [],[],[]
        for (x_pix,y_pix),(x_disp,y_disp),(x_dat,y_dat) in zip(self.xy_pixels, xy_display,xy_data):
            # Ignore display points that weren't transformable (too far from the projection)
            if np.isnan(x_dat) or np.isnan(y_dat):
                continue
            # Ignore display points that lie outside the projection
            if not self.axes.axes.patch.contains_point((x_disp, y_disp)):
                continue
            col = self.colours[y_pix, x_pix]
            if ignore_white and np.all(col == c_white):
                continue
            valid_x.append(x_dat)
            valid_y.append(y_dat)
            valid_col.append(col)

        # This is our recovered representation of the source data in its original frame
        valid_sc = SkyCoord(valid_x, valid_y, unit = u.deg, frame = coord_frame)
        return valid_sc,valid_col
