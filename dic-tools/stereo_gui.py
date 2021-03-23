import os

os.environ['KIVY_NO_ARGS'] = '1'
import sys
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
import acquistion as cam_aq
from pathlib import Path
from kivy.lang import Builder
import kivymd.utils.asynckivy as ak
import PySpin
import numpy as np
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.image import Image
from kivy.properties import BoundedNumericProperty, ReferenceListProperty, BooleanProperty, NumericProperty, \
    StringProperty
from kivy.core.window import Window
from loguru import logger

Window.minimum_width = '725dp'
Window.minimum_height = '550dp'


class FLIRImage(Image):
    pass


# main page inspiration: https://imgur.com/a3IcAZN
class FLIRCamera(MDBoxLayout):
    acquiring = BooleanProperty(False)
    gain = BoundedNumericProperty(5, min=0, max=27)
    exposure_time = NumericProperty()
    fps = NumericProperty()
    cam_settings = ReferenceListProperty(acquiring, gain, exposure_time, fps)
    image_id = NumericProperty(0)

    def __init__(self, camera, **kwargs):
        super(FLIRCamera, self).__init__(**kwargs)
        self.hardware_cam = camera
        self.frame_id = -1
        self.image = None
        self.serial_number = None

    def on_acquiring(self, switch, value):
        # self.acquiring = value
        if value:
            self.hardware_cam.BeginAcquisition()
            logger.debug('Acquisition started.')
        else:
            self.hardware_cam.EndAcquisition()
            logger.debug('Acquisition ended.')

    def on_gain(self, source, value):
        self.hardware_cam.Gain.SetValue(value)
        logger.debug(f'Gain set to {value}')

    def on_exposure_time(self, source, value):
        self.hardware_cam.ExposureTime.SetValue(value)
        logger.debug(f'Exposure time set to {value}')

    def on_fps(self, source, value):
        self.hardware_cam.AcquisitionFrameRate.SetValue(value)
        logger.debug(f'Frame rate set to {value}')

    async def configure_camera(self, fps, exposure_time, acquisition_mode='Continuous', buffer_mode='NewestOnly'):

        # Set acquisition mode to continuous
        if self.serial_number is None:
            self.serial_number = self.hardware_cam.DeviceSerialNumber.GetValue()
        logger.debug('Serial Number Grabbed')
        node_acquisition_mode = self.hardware_cam.AcquisitionMode
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            logger.error('Unable to set acquisition mode to continuous (node retrieval; camera). Aborting... \n')
            return False
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName(acquisition_mode)
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
                node_acquisition_mode_continuous):
            logger.error(f'Unable to set acquisition mode to {acquisition_mode} (entry \'continuous\' retrieval). \
            Aborting... \n')
            return False
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
        logger.debug(f'Camera acquisition mode set to {acquisition_mode}...')
        # Set StreamBuferHandlingMode to NewestOnly
        s_node_map = self.hardware_cam.GetTLStreamNodeMap()
        node_buffer_handling_mode = PySpin.CEnumerationPtr(s_node_map.GetNode('StreamBufferHandlingMode'))
        if not PySpin.IsAvailable(node_buffer_handling_mode) or not PySpin.IsWritable(node_buffer_handling_mode):
            logger.error('Unable to set buffer mode to newest only (node retrieval; camera). Aborting... \n')
            return False
        node_buffer_handling_mode_newest = node_buffer_handling_mode.GetEntryByName(buffer_mode)
        if not PySpin.IsAvailable(node_buffer_handling_mode_newest) or not PySpin.IsReadable(
                node_buffer_handling_mode_newest):
            logger.error(f'Unable to set buffer mode to {buffer_mode} (entry \'continuous\' retrieval ). \
            Aborting... \n')
            return False
        buffer_handling_newest = node_buffer_handling_mode_newest.GetValue()
        node_buffer_handling_mode.SetIntValue(buffer_handling_newest)
        logger.debug(f'Camera buffer handling mode set to {buffer_mode}')
        # turn auto gain, exposure, acquisition rate off
        exposure_auto = self.hardware_cam.ExposureAuto
        if exposure_auto.GetAccessMode() != PySpin.RW:
            logger.error('Unable to disable automatic exposure. Aborting...')
            return False
        exposure_auto.SetValue(PySpin.ExposureAuto_Off)
        # self.hardware_cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)  # to re-enable exposure
        logger.info('Automatic exposure disabled')
        self.hardware_cam.exposure_time = exposure_time
        gain_auto = self.hardware_cam.GainAuto
        if gain_auto.GetAccessMode() != PySpin.RW:
            logger.error('Unable to disable automatic exposure. Aborting...')
            return False
        gain_auto.SetValue(PySpin.GainAuto_Off)
        # self.hardware_cam.GainAuto.SetValue(PySpin.GainAuto_Continuous)  # to re-enable exposure
        logger.info('Automatic gain disabled')
        self.hardware_cam.gain = self.gain
        # self.hardware_cam.GainAuto.SetValue(PySpin.GainAuto_Continuous)  # to re-enable exposure
        self.hardware_cam.AcquisitionFrameRateEnable.SetValue(True)
        self.hardware_cam.fps = fps
        # cam_aq.configure_trigger(self.hardware_cam)

    async def get_next_image(self, app, save_image=False, update_view=True, stop_stream=False):
        # trigger?
        logger.debug(f'{self.serial_number} Acquiring')
        image_result = self.hardware_cam.GetNextImage()
        current_frame_id = image_result.GetFrameID()
        logger.debug('Image Result Grabbed')
        if not image_result.IsIncomplete() and self.frame_id != current_frame_id:
            self.image = image_result
            self.frame_id = current_frame_id
            width = image_result.GetWidth()
            height = image_result.GetHeight()
            if update_view:
                image_arr = image_result.GetNDArray()
                logger.debug(f'{self.serial_number} Array Gotten')
                arr = np.copy(np.flipud(image_arr)).tobytes()
                image_texture = Texture.create(size=(width, height), colorfmt='luminance')
                image_texture.blit_buffer(arr, colorfmt='luminance')
                logger.debug(f'{self.serial_number} Texture blitted')
                image_view = self.ids['image_view']
                image_view.texture = image_texture
                logger.debug(f'{self.serial_number} Texture assigned')
            if save_image or app.record_stream:
                ak.start(self.save_image(app, image_result))
                self.image_id += 1
            if stop_stream:
                self.ids['stream_switch'].active = False

    async def save_image(self, app, image_result):
        with cam_aq.working_directory(app.screen.ids['settings_grid'].ids['save_dir_input'].text):
            image_converted = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
            image_id_str = f'{"0" * (3 - len(str(self.image_id)))}{self.image_id}'
            filename = f'{app.project_name}_{image_id_str}_S#{self.serial_number}.jpg'
            # Save image
            image_converted.Save(filename)
            logger.debug('Image saved at %s' % filename)


class SettingsGrid(MDBoxLayout):
    # todo set number of cameras (must be equal to or less than available cameras)
    # todo run until (n images, for time, until stopped)
    def __init__(self, **kwargs):
        super(SettingsGrid, self).__init__(**kwargs)

    def snap_picture(self, app):
        # save current images (one shot).
        directory = Path(self.ids['save_dir_input'].text)
        if directory.is_dir() is True and str(directory) != '.':
            for cam in app.cam_list:
                # stop streaming on all cameras
                if cam.acquiring is False:
                    cam.ids['stream_switch'].active = True
                # take picture with all cameras
                ak.start(cam.get_next_image(app, save_image=True, stop_stream=True))
            # app.image_id += 1
        else:
            self.ids['save_dir_input'].focus = True
            self.ids['save_dir_input'].focus = False

    def record_stream(self, record_button, app):
        directory = Path(self.ids['save_dir_input'].text)
        if directory.is_dir() is True and str(directory) != '.':
            if app.record_stream is False:  # start recording
                record_button.md_bg_color = app.theme_cls.error_color
                record_button.tooltip_text = 'Recording'
                app.record_stream = True
                for cam in app.cam_list:  # start stream if not already streaming
                    if cam.acquiring is False:
                        cam.ids['stream_switch'].active = True
            else:  # stop recording
                record_button.md_bg_color = app.theme_cls.primary_color
                record_button.tooltip_text = 'Record Stream'
                app.record_stream = False
        else:
            self.ids['save_dir_input'].focus = True
            self.ids['save_dir_input'].focus = False


class StereoCamerasApp(MDApp):
    # camera settings are linked to app level properties
    main_exposure_time = BoundedNumericProperty(100, min=100, max=1000000)  # units are microseconds
    main_fps = BoundedNumericProperty(16.5, min=1.33, max=19)
    project_name = StringProperty('DIC Project')
    record_stream = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(StereoCamerasApp, self).__init__(**kwargs)
        print(self.built)

    def build(self):
        # async_loop = asyncio.get_event_loop()
        # main(async_loop)
        self.theme_cls.theme_style = 'Light'
        self.theme_cls.primary_palette = 'BlueGray'
        self.screen = Builder.load_file('StereoGUI.kv')
        self.camera_box = self.screen.ids['camera_box']
        ak.start(self.connect_flir_system())
        return self.screen

    def on_start(self):
        Clock.schedule_interval(self.run_cameras, 1.0 / 60.0)

    def on_stop(self):
        # todo release images and uninit any active cameras
        ak.start(self.connect_flir_system(False))

    def on_main_exposure_time(self, source, value):
        for cam in self.cam_list:
            cam.exposure_time = value

    def on_main_fps(self, source, value):
        for cam in self.cam_list:
            cam.fps = value

    async def connect_flir_system(self, connect=True):
        if connect:
            self.system = PySpin.System.GetInstance()
            # Retrieve list of cameras from the system
            cameras = self.system.GetCameras()
            self.cam_list = [FLIRCamera(cam) for cam in cameras]
            cameras.Clear()
            for cam in self.cam_list:
                self.camera_box.add_widget(cam)
                cam.hardware_cam.Init()
                ak.start(cam.configure_camera(self.main_fps, self.main_exposure_time))
        else:
            for camera in self.cam_list:
                # camera.hardware_cam.DeInit()
                # todo restore default settings
                del camera.hardware_cam  # clears reference to camera
            self.cam_list.clear()
            self.camera_box.clear_widgets()  # removes created image views
            self.system.ReleaseInstance()
            del self.system

    def run_cameras(self, dt):
        for cam in self.cam_list:
            if cam.acquiring:
                ak.start(cam.get_next_image(self, update_view=True))

    def reset_camera_system(self):
        ak.start(self.connect_flir_system(connect=False))
        ak.start(self.connect_flir_system())


if __name__ == '__main__':
    logger.remove()
    logger.add(sys.stderr, level='INFO')
    StereoCamerasApp().run()
