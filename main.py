#__version__ = '1.0'

''' 
This script is adapted from the gallery example: "Touch Tracer Line Drawing Demonstration"
(https://kivy.org/doc/stable/examples/gen_demo_touchtracer_main_py.html)

..note from the original script::

    A function 'calculate_points' handling the points which will be drawn
    has by default implemented a delay of 5 steps. To get more precise visual
    results lower the value of the optional keyword argument 'steps'.

..points modified::

    The original script         |  Adapted script
    ----------------------------------------
    - uses particle.png file    | - no trail visible
      as the source for drawing | 
      the trails                |
    - cross-hairs with          | - no cross-hair/
      the coordinates next to   |   no coordinates info
      the touched point         |

..points added::

    There are four circular targets that a user needs to pass.
    Once the touch gets near the center of the targets,
    the colors of the targets will change to bright white.
    The targets need to be visited in a pre-defined order.
    Otherwise, they will never turn white.

    When all targets are visited, their colors will be recovered.
    A user needs to go through the process several times in total.
    The number of repetition can be set in the parameter screen.
'''
 

import kivy 
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Point, GraphicException
from random import random
from math import sqrt
from kivy.metrics import cm
import time
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, NumericProperty
from kivy.storage.jsonstore import JsonStore
from kivy import platform

timestamp = time.strftime("%Y%m%d_%H:%M:%S")

from jnius import autoclass, cast 
def _get_activity():

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    activity = PythonActivity.mActivity

    if activity is None:
        # assume we're running from the background service
        PythonService = autoclass('org.kivy.android.PythonService')
        activity = PythonService.mService
    return activity


if platform == 'android': 

    from android.permissions import request_permissions, Permission 
    request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

    '''
    try:
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
    except JavaException:
        PythonActivity = autoclass('org.renpy.android.PythonActivity')
    '''

    activity = _get_activity()
    currentActivity = cast('android.app.Activity', activity)
    context = cast('android.content.ContextWrapper', currentActivity.getApplicationContext())
    file_p = cast('java.io.File', context.getFilesDir())
    private_storage = os.path.normpath(os.path.abspath(file_p.getAbsolutePath().replace("/", os.path.sep)))

    store = JsonStore(".".join([private_storage, timestamp, 'json']))
else:
    store = JsonStore(".".join([timestamp, 'json']))

def calculate_points(x1, y1, x2, y2, steps=5):
    dx = x2 - x1
    dy = y2 - y1
    dist = sqrt(dx * dx + dy * dy)
    if dist < steps:
        return
    o = []
    m = dist / steps
    for i in range(1, int(m)):
        mi = i / m
        lastx = x1 + dx * mi
        lasty = y1 + dy * mi
        o.extend([lastx, lasty])
    return o

class ParamPopup(Popup):
    pass

class DonePopup(Popup):
    pass

class ParamScreen(Screen):
    
    gender = ObjectProperty(None)
    handed_chk = ObjectProperty(False)

    def show_popup(self):

        the_popup = ParamPopup(title = 'READ IT', size_hint = (None, None), size = (400, 400))
        
        # If any of the items are not filled in, you can't proceed to the next screen
        if any([self.pid_text_input.text == "", self.age_text_input == "", self.gender == None, self.handed_chk == False]): 
            the_popup.argh.text = "Missing values!" 
            the_popup.open()

        else:
            subid = "_".join(["SUBJ", self.pid_text_input.text])
            subj_info = {'age': self.age_text_input.text, 'gender': self.gender,
                    'right_used': self.ids.rightchk.active}
            store.put(subid, subj_info = subj_info)
            self.parent.current = "touchtracer"

    def if_active_m(self, state):
        if state:
            self.gender = "M"

    def if_active_f(self, state):
        if state:
            self.gender = "F"

    def if_active_hnd(self, state):
        self.handed_chk = True

class Touchtracer(Screen):

    def on_touch_down(self, touch):
        win = self.get_parent_window()
        ud = touch.ud
        ud['group'] = g = str(touch.uid)
        pointsize = 3
        if 'pressure' in touch.profile:
            ud['pressure'] = touch.pressure
            pointsize = (touch.pressure * 100000) ** 2
        ud['color'] = random()

        with self.canvas:
            Color(ud['color'], 1, 1, mode='hsv', group=g)
            ud['lines'] = [
                #Rectangle(pos=(touch.x, 0), size=(1, win.height), group=g),
                #Rectangle(pos=(0, touch.y), size=(win.width, 1), group=g),
                Point(points=(touch.x, touch.y), source='particle.png',
                      pointsize=pointsize, group=g)]

        ud['label'] = Label(size_hint=(None, None))
        self.update_touch_label(ud['label'], touch)
        self.add_widget(ud['label'])
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return
        ud = touch.ud
        #ud['lines'][0].pos = touch.x, 0
        #ud['lines'][1].pos = 0, touch.y

        index = -1

        while True:
            try:
                points = ud['lines'][index].points
                oldx, oldy = points[-2], points[-1]
                break
            except:
                index -= 1

        points = calculate_points(oldx, oldy, touch.x, touch.y)

        # if pressure changed create a new point instruction
        if 'pressure' in ud:
            if not .95 < (touch.pressure / ud['pressure']) < 1.05:
                g = ud['group']
                pointsize = (touch.pressure * 100000) ** 2
                with self.canvas:
                    Color(ud['color'], 1, 1, mode='hsv', group=g)
                    ud['lines'].append(
                        Point(points=(), source='particle.png',
                              pointsize=pointsize, group=g))

        if points:
            try:
                lp = ud['lines'][-1].add_point
                for idx in range(0, len(points), 2):
                    lp(points[idx], points[idx + 1])
            except GraphicException:
                pass

        ud['label'].pos = touch.pos
        t = int(time.time())
        if t not in ud:
            ud[t] = 1
        else:
            ud[t] += 1
        self.update_touch_label(ud['label'], touch)

        # 'eps' is the threshold value for the position of a touch.
        # If the x and y coordinatates of the touch are both within the
        # square boundary whose sides all have the length of 'eps',
        # then the target turns white.
        eps = cm(self.ids.t1.diameter*0.3) 

        white = (1, 1, 1, 1)

        # The first target will turn white when the touch is near its center
        if all([abs(ud['label'].pos[0] - float(self.ids.t1.xcoord)) < eps, 
            abs(ud['label'].pos[1] - float(self.ids.t1.ycoord)) < eps]):
            self.ids.t1.customcolor = white
            self.ids.t1.is_touched = 1

        # The second target will turn white if the touch is near its center
        # and if the first target had been visited previously
        if all([self.ids.t1.is_touched == 1, 
            abs(ud['label'].pos[0] - float(self.ids.t2.xcoord)) < eps, 
            abs(ud['label'].pos[1] - float(self.ids.t2.ycoord)) < eps]):
            self.ids.t2.customcolor = white
            self.ids.t2.is_touched = 1

        if all([self.ids.t2.is_touched == 1,
            abs(ud['label'].pos[0] - float(self.ids.t3.xcoord)) < eps,
            abs(ud['label'].pos[1] - float(self.ids.t3.ycoord)) < eps]):
            self.ids.t3.customcolor = white
            self.ids.t3.is_touched = 1

        # The fourth target should wait until the previous three are
        # 'lightened up'
        if all([self.ids.t3.is_touched == 1,
            abs(ud['label'].pos[0] - float(self.ids.t4.xcoord)) < eps,
            abs(ud['label'].pos[1] - float(self.ids.t4.ycoord)) < eps]):
            self.ids.t4.customcolor = white
            self.ids.t4.is_touched = 1

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return
        touch.ungrab(self)
        ud = touch.ud
        self.canvas.remove_group(ud['group'])
        self.remove_widget(ud['label'])

        red = (1, 0, 0, 0.5)
        green = (0, 1, 0, 0.5)
        blue = (0, 0, 1, 0.5)
        purple = (0.5, 0.5, 1, 0.5)

        # When all targets are visited, their original colors will be retrieved 
        if all([self.ids.t1.is_touched, self.ids.t2.is_touched, self.ids.t3.is_touched, self.ids.t4.is_touched]):
            self.ids.t1.customcolor = red
            self.ids.t1.is_touched = 0
            self.ids.t2.customcolor = green
            self.ids.t2.is_touched = 0
            self.ids.t3.customcolor = blue
            self.ids.t3.is_touched = 0
            self.ids.t4.customcolor = purple
            self.ids.t4.is_touched = 0
            self.ids.t4.all_touched += 1
            print(self.ids.t4.all_touched)

        if (self.ids.t4.all_touched >= 3):
            self.ids.t4.all_touched = 0
            popup2 = DonePopup(title = "READ IT", size_hint = (None, None), size = (400, 400))
            popup2.argh.text = "Completed"
            popup2.open()

    def update_touch_label(self, label, touch):
        #label.text = 'ID: %s\nPos: (%d, %d)\nClass: %s' % (
        #    touch.id, touch.x, touch.y, touch.__class__.__name__)
        label.texture_update()
        label.pos = touch.pos
        label.size = label.texture_size[0] + 20, label.texture_size[1] + 20
        # The way time / position stored could be improved...
        store.put(str(touch.time_update), pos = [str(touch.x), str(touch.y)])

class FinishScreen(Screen):

    def start_new(self):
        self.parent.ids.paramsc.pid_text_input.text = ""
        self.parent.ids.paramsc.age_text_input.text = ""
        self.parent.ids.paramsc.male_chkbox.active = False
        self.parent.ids.paramsc.female_chkbox.active = False
        self.parent.ids.paramsc.left_chkbox.active = False
        self.parent.ids.paramsc.right_chkbox.active = False
        self.parent.current = "param_screen"

class screen_manager(ScreenManager):
    pass

class TouchtracerApp(App):
    #title = 'Touchtracer'
    #icon = 'icon.png'

    def build(self):
        return screen_manager(transition=FadeTransition())

    def on_pause(self):
        return True


if __name__ == '__main__':
    TouchtracerApp().run()
