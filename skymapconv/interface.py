import astropy.units as u
import cartopy.crs as ccrs
import matplotlib.collections as mpl_collections
import matplotlib.gridspec as mpl_gridspec
import matplotlib.pyplot as plt
import matplotlib.widgets as mpl_widgets
import numpy as np
from astropy.coordinates import SkyCoord, SphericalRepresentation

from .extractor import Extractor


def get_lonlat(coord: SkyCoord, rep_frame: str):
    """For a given SkyCoord, transform it to the frame named rep_frame and then
    return the longitude and latitude components. Mostly the point of this
    function is to handle the component name mapping that Astropy applies
    (ie, 'lon' is usually called 'ra' instead, or 'l' for the Galactic
    coordinate system, or 'sgl' for Supergalactic, etc)."""
    # Assumes SkyCoord inherits SphericalRepresentation, which for our cases
    # will be true
    rep = coord.transform_to(rep_frame).represent_as(SphericalRepresentation)
    return rep.lon.to('deg'),rep.lat.to('deg')


class Interface():
    """Wrap the Extractor class in some UI tools for aligning the extraction
    target and choosing the input and output projections and coordinate frames.
    Should work equally well when run from the command line or within Jupyter."""

    SC_EQUATOR = SkyCoord(ra = np.linspace(-360, 360, 100), dec = 0,
        unit = u.deg, frame = 'icrs')
    SC_GALCEN = SkyCoord(l = 0, b = 0,
        unit = u.deg, frame = 'galactic')
    SC_GALPLANE = SkyCoord(l = np.linspace(-360, 360, 100), b = 0,
        unit = u.deg, frame = 'galactic')
    SC_SUPERGALPLANE = SkyCoord(sgl = np.linspace(-360, 360, 100), sgb = 0,
        unit = u.deg, frame = 'supergalactic')
    UI_BUTTON_TEXT = "Extract data with current alignment"

    def __init__(self, filepath: str):
        self.proj_list = ('Hammer', 'Aitoff', 'Sinusoidal')
        self.frame_list = ('icrs', 'galactic')
        self.frame_ui_mapping = {'icrs': "Equatorial", 'galactic': "Galactic"}

        # Controls for the "Input" figure
        self.input_tog = {
            'Show equatorial plane': True,
            'Show galactic centre': True,
            'Show galactic plane': True,
            'Show supergalactic plane': False,
        }
        self.input_tog_artists = {k:None for k in self.input_tog.keys()}
        self.input_frame_current = 0
        self.input_proj_current = 0
        self.input_clon_current = 0

        # Controls for the "Output" figure
        self.output_frame_current = 1
        self.output_proj_current = 0
        self.output_clon_current = 0
        self.output_rad_current = 1.2

        self.extractor = Extractor(filepath)
        self._redecorate_input_axes()

        self.fig_control = plt.figure(num = "Control window")
        self.fig_control.set_size_inches(8,3)

        self.fig_output = plt.figure(num = "Output")
        self.fig_output.set_size_inches(8,6)
        self.ax_output = None
        self.out_data = None
        self.out_patches = None
        self.transData = None
        self._make_output_axes()

        self._make_controls()

    def show(self):
        """Make an event loop and wait for all plots to be closed."""
        # https://github.com/matplotlib/matplotlib/issues/7338
        plt.show(block = True)

    def _redecorate_input_axes(self):
        proj_name = self.proj_list[self.input_proj_current]
        frame_name = self.frame_list[self.input_frame_current]

        # This may automatically destroy and recreate the Axes
        self.extractor.projection = proj_name
        self.extractor.central_longitude = self.input_clon_current

        for key in self.input_tog_artists.keys():
            if self.input_tog_artists[key] is not None:
                self.input_tog_artists[key].remove()
                self.input_tog_artists[key] = None

        # In case the Axes weren't actually destroyed and remade, we want to
        # reset the ordering of the colours anyway before we remake our artists
        self.extractor.axes.set_prop_cycle(None)

        self.input_tog_artists['Show supergalactic plane'] = self.extractor.axes.plot(
            *get_lonlat(self.SC_SUPERGALPLANE, frame_name), '-', transform = ccrs.Geodetic())[0]
        self.input_tog_artists['Show equatorial plane'] = self.extractor.axes.plot(
            *get_lonlat(self.SC_EQUATOR, frame_name), '-', transform = ccrs.Geodetic())[0]
        self.input_tog_artists['Show galactic plane'] = self.extractor.axes.plot(
            *get_lonlat(self.SC_GALPLANE, frame_name), '-', transform = ccrs.Geodetic())[0]
        self.input_tog_artists['Show galactic centre'] = self.extractor.axes.plot(
            *get_lonlat(self.SC_GALCEN, frame_name), '.', transform = ccrs.Geodetic())[0]

        for key,visib in self.input_tog.items():
            self.input_tog_artists[key].set_visible(visib)

    def _make_output_axes(self):
        if self.ax_output is not None:
            self.ax_output.remove()
            self.ax_output = None

        proj_name = self.proj_list[self.output_proj_current]
        proj_class = getattr(ccrs, proj_name)
        proj = proj_class(central_longitude = self.output_clon_current)
        self.ax_output = self.fig_output.add_subplot(projection = proj)

        self.ax_output.set_global() # Full projection axes extent
        self.ax_output.set_xlim(self.ax_output.properties()['xlim'][::-1]) # Reverse for sky map
        # Add gridlines
        # self.ax_output.gridlines(draw_labels = True, formatter_kwargs = dict(direction_label = False))

        # TODO: Add options for how this axis is formatted, eg with gridlines, axis ticks, etc

        self.transData = ccrs.Geodetic()._as_mpl_transform(axes = self.ax_output)
        self._update_output_patches()

    def _make_controls(self):
        gs_f = mpl_gridspec.GridSpec(2, 2, figure = self.fig_control, height_ratios = [1, 3])

        gs_t = gs_f[0:2].subgridspec(3, 1)
        # for gs in gs_t:
        #     self.fig_control.add_subplot(gs)
        # self.fig_control.axes[0].set_title("hello", loc = "left")

        gs_l = gs_f[2].subgridspec(3, 2, height_ratios = [4, 3, 0.5])
        ax_input_tog   = self.fig_control.add_subplot(gs_l[0, :])
        ax_input_frame = self.fig_control.add_subplot(gs_l[1, 0])
        ax_input_proj  = self.fig_control.add_subplot(gs_l[1, 1])
        ax_input_clon  = self.fig_control.add_subplot(gs_l[2, :])
        ax_input_tog.set_title("Input configuration", loc = 'left')

        gs_r = gs_f[3].subgridspec(4, 2, height_ratios = [3, 3, 0.5, 0.5])
        ax_output_draw  = self.fig_control.add_subplot(gs_r[0, :])
        ax_output_frame = self.fig_control.add_subplot(gs_r[1, 0])
        ax_output_proj  = self.fig_control.add_subplot(gs_r[1, 1])
        ax_output_clon  = self.fig_control.add_subplot(gs_r[2, :])
        ax_circ_output  = self.fig_control.add_subplot(gs_r[3, :])
        ax_output_draw.set_title("Output configuration", loc = 'left')

        # def format_axes(fig):
        #     for i, ax in enumerate(fig.axes):
        #         ax.text(0.5, 0.5, f"ax{i+1}", va = 'center', ha = 'center')
        #         ax.tick_params(labelbottom = False, labelleft = False)
        # format_axes(self.fig_control)

        axs_pos = {}
        self.sliders_pos = {}
        for gs,key in zip(gs_t, ['xmid', 'ymid', 'width', 'height']):
            if key == 'height': # leave height fixed at 1, we don't need to control it.
                break
            if 'mid' in key:
                label = f"{key[0].upper()}"
            else:
                label = key.capitalize()
            axs_pos[key] = self.fig_control.add_subplot(gs)
            self.sliders_pos[key] = mpl_widgets.Slider(axs_pos[key], label, 0, 1,
                valinit = getattr(self.extractor, key))
            # Have to store the value of 'key' at definition like this. https://stackoverflow.com/a/63123379
            self.sliders_pos[key].on_changed(lambda val, key=key: self._update_input_position(val, key))
        list(axs_pos.values())[0].set_title("Alignment", loc = 'left')

        self.wgt_input_frame = mpl_widgets.RadioButtons(ax_input_frame, [self.frame_ui_mapping[key] for key in self.frame_list], active = self.input_frame_current)
        self.wgt_input_frame.on_clicked(self._update_input_frame)

        self.wgt_input_proj = mpl_widgets.RadioButtons(ax_input_proj, self.proj_list, active = self.input_proj_current)
        self.wgt_input_proj.on_clicked(self._update_input_proj)

        self.wgt_input_clon = mpl_widgets.Slider(ax_input_clon, "Central lon.", 0, 270,
            valinit = self.input_clon_current, valstep = 90)
        self.wgt_input_clon.on_changed(self._update_input_clon)

        self.wgt_input_tog = mpl_widgets.CheckButtons(ax_input_tog, self.input_tog.keys(), actives = self.input_tog.values())
        self.wgt_input_tog.on_clicked(self._update_input_toggle)

        self.wgt_output_button = mpl_widgets.Button(ax_output_draw, self.UI_BUTTON_TEXT)
        self.wgt_output_button.on_clicked(self._update_extracted_data)

        self.wgt_output_frame = mpl_widgets.RadioButtons(ax_output_frame, [self.frame_ui_mapping[key] for key in self.frame_list], active = self.output_frame_current)
        self.wgt_output_frame.on_clicked(self._update_output_frame)

        self.wgt_output_proj = mpl_widgets.RadioButtons(ax_output_proj, self.proj_list, active = self.output_proj_current)
        self.wgt_output_proj.on_clicked(self._update_output_proj)

        self.wgt_output_clon = mpl_widgets.Slider(ax_output_clon, 'Central lon.', 0, 270,
            valinit = self.output_clon_current, valstep = 90)
        self.wgt_output_clon.on_changed(self._update_output_clon)

        self.wgt_output_rad = mpl_widgets.Slider(ax_circ_output, 'Smoothing', 0, 1.5,
            valinit = self.output_rad_current)
        self.wgt_output_rad.on_changed(self._update_output_rad)

        self.fig_control.tight_layout()

    def _update_input_position(self, val, key):
        self.extractor.update_position(**{key: val})

    def _update_input_toggle(self, label):
        if label is None:
            for key in self.input_tog.keys():
                self.input_tog[key] = False
        else:
            self.input_tog[label] = not self.input_tog[label]
        for key,visib in self.input_tog.items():
            artist = self.input_tog_artists[key]
            artist.set_visible(visib)
        self.extractor.draw_idle()

    def _update_input_frame(self, _):
        self.input_frame_current = self.wgt_input_frame.index_selected
        self._redecorate_input_axes()
        self.extractor.draw_idle()

    def _update_input_proj(self, _):
        self.input_proj_current = self.wgt_input_proj.index_selected
        self._redecorate_input_axes()
        self.extractor.draw_idle()

    def _update_input_clon(self, val):
        self.input_clon_current = val
        self._redecorate_input_axes()
        self.extractor.draw_idle()

    def _update_output_frame(self, _):
        self.output_frame_current = self.wgt_output_frame.index_selected
        self._make_output_axes()

    def _update_output_proj(self, _):
        self.output_proj_current = self.wgt_output_proj.index_selected
        self._make_output_axes()

    def _update_output_clon(self, val):
        self.output_clon_current = val
        self._make_output_axes()

    def _update_extracted_data(self, _):
        self.wgt_output_button.label.set_text("Running...")
        self.fig_control.canvas.draw() # Force the draw now, only works in jupyter though
        try:
            frame_in = self.frame_list[self.input_frame_current]
            self.out_data = self.extractor.get_data(frame_in)
            self.wgt_output_button.label.set_text(self.UI_BUTTON_TEXT)
            self.fig_control.canvas.draw_idle()
        except Exception:
            self.out_data = None
            self.wgt_output_button.label.set_text("Error")
            self.fig_control.canvas.draw_idle()
        self._update_output_patches()

    def _update_output_patches(self):
        if self.out_patches is not None:
            self.out_patches.remove()
            self.out_patches = None
        if self.out_data is None:
            return
        else:
            valid_sc,valid_col = self.out_data
        frame_out = self.frame_list[self.output_frame_current]
        # In principle we could optimise a bit harder around keeping this set of
        # coordinates after we converted it, because sometimes we don't need to
        # recalculate it to draw the patches. It's fairly fast though
        positions = [(x.value,y.value) for x,y in zip(*get_lonlat(valid_sc, frame_out))]
        self.out_patches = mpl_collections.CircleCollection(
            sizes = np.pi*self.output_rad_current**2 * np.ones(len(positions)),
            offsets = positions, offset_transform  = self.transData, edgecolors = 'face',
            facecolors = valid_col,
        )
        self.ax_output.add_collection(self.out_patches)
        self.fig_output.canvas.draw_idle()

    def _update_output_rad(self, val):
        self.output_rad_current = val
        if self.out_patches is None:
            return
        self.out_patches.set_sizes(np.pi*val**2 * np.ones(len(self.out_patches.get_sizes())))
        self.fig_output.canvas.draw_idle()
