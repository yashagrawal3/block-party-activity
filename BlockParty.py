#  Block Party Activity for OLPC
#  by Vadim Gerasimov
#  updated 23 Feb 2007

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango
from gi.repository import PangoCairo
import operator
import time
import string
import math
import pickle
import getopt
import sys
import random
import copy
import socket
import os


class Color:
    def __init__(self, gdk_color):
        self.red = gdk_color.red / 65535.0
        self.green = gdk_color.green / 65535.0
        self.blue = gdk_color.blue / 65535.0

class BlockParty:

    bwpx,bhpx,score,bw,bh,glass,cnt=0,0,0,11,20,[],0
    xshift, yshift = 0, 0
    colors = ['black', 'blue', 'green', 'cyan', 'red', 'magenta','YellowGreen', 'white']
    figures = [[[0,0,0,0],
          [0,1,1,0],
          [0,1,1,0],
          [0,0,0,0]],
         [[0,0,0,0],
          [0,2,2,0],
          [2,2,0,0],
          [0,0,0,0]],
         [[0,0,0,0],
          [3,3,0,0],
          [0,3,3,0],
          [0,0,0,0]],
         [[0,0,0,0],
          [4,4,4,4],
          [0,0,0,0],
          [0,0,0,0]],
         [[0,0,0,0],
          [0,5,5,5],
          [0,5,0,0],
          [0,0,0,0]],
         [[0,0,0,0],
          [6,6,6,0],
          [0,6,0,0],
          [0,0,0,0]],
         [[0,0,0,0],
          [0,7,0,0],
          [0,7,7,7],
          [0,0,0,0]]]

    left_key  = ['Left', 'KP_Left']
    right_key  = ['Right', 'KP_Right']
    drop_key  = ['space', 'KP_Down']
    rotate_key = ['Up', 'KP_Up']
    exit_key = ['Escape']
    sound_toggle_key = ['s', 'S']
    enter_key  = ['Return']

    figure,px,py = None, 0, 0

    next_figure = None
    xnext, ynext = 0, 0

    tickcnt = 0
    cm = None
    area = None
    windows = None
    linecount = 0
    score = 0
    level = 0
    figure_score = 0
    scorefont = None
    color_back, color_glass, color_score = None, None, None

    scorex, scorey = 20, 100

    time_step, next_tick = 100, time.time()+100

    complete_update, glass_update, next_update, score_update = False, False, False, False

    IDLE, SELECT_LEVEL, PLAY, GAME_OVER = 0, 1, 2, 3

    game_mode = IDLE

    sound = False
    soundon = True
    cssock = None
    csid = 544554

    def draw_glass(self, cairo_ctx):
       draw_glass = copy.deepcopy(self.glass)
       for i in range(4):
          for j in range(4):
             if self.py+i < self.bh and self.figure[i][j] != 0:
                draw_glass[self.py+i][self.px+j]=self.figure[i][j]

       for i in range(self.bh):
          for j in range(self.bw):
             if self.view_glass is None or draw_glass[i][j] != self.view_glass[i][j]: 
                 color = self.colors[draw_glass[i][j]]
                 cairo_ctx.set_source_rgb(color.red,
                                          color.green,
                                          color.blue)
                 cairo_ctx.rectangle(self.xshift+j*self.bwpx, self.yshift+(self.bh-i-1)*self.bhpx, self.bwpx, self.bhpx)

                 cairo_ctx.fill()

       self.view_glass = draw_glass

    def quit_game(self):
       sys.exit()

    def key_action(self, key):
       if key in self.exit_key: self.quit_game()
       if key in self.sound_toggle_key: 
           self.soundon = not self.soundon
           return
       if self.game_mode == self.SELECT_LEVEL:
          if key in self.left_key:
             self.set_level(self.level-1)
             self.queue_draw_glass(True)
          else:
              if key in self.right_key:
                  self.set_level(self.level+1)
                  self.queue_draw_glass(True)
              else: # if key in enter_key:
                  self.queue_draw_complete()
                  self.next_tick = time.time()+self.time_step
                  self.game_mode = self.PLAY
#      try: new_level = int(key)
#      except: new_level = -1
#      if new_level >= 0 and new_level <= 9: 
#         set_level(new_level)
#         game_mode = PLAY
          return
       if self.game_mode == self.IDLE:
          return
       if self.game_mode == self.GAME_OVER:
#         print 'Starting new game...'
          self.init_game()
          return 
       changed = False
       if key in self.left_key:
          self.px-=1 
          if not self.figure_fits(): self.px+=1
          else: changed=True
       if key in self.right_key:
          self.px+=1 
          if not self.figure_fits(): self.px-=1
          else: changed=True
       if key in self.drop_key:
          changed = self.drop_figure()
       if key in self.rotate_key:
          changed = self.rotate_figure_ccw(True)
       if changed:
          self.queue_draw_glass(False)

    def tick(self):
       self.py-=1
       self.queue_draw_glass(False)
       if self.figure_score > 0: self.figure_score -= 1
       if not self.figure_fits():
          self.py+=1
          self.put_figure()
          self.make_sound('heart.wav')
          self.new_figure()
          if not self.figure_fits():
             i = random.randint(0, 2)
             if i is 0: self.make_sound('ouch.wav')
             if i is 1: self.make_sound('wah.au'),
             if i is 2: self.make_sound('lost.wav')
             print 'GAME OVER: score ' + str(self.score)
             self.game_mode = self.GAME_OVER
             self.complete_update = True

             self.queue_draw_complete()
             return
#             quit_game()
#      window.queue_draw()
       self.chk_glass()
       new_level = int(self.linecount/5)
       if new_level > self.level: self.set_level(new_level)

    def new_figure(self):
       self.figure_score = self.bh + self.level
       self.figure = copy.deepcopy(self.figures[random.randint(0,len(self.figures)-1)])
       for i in range(random.randint(0, 3)): self.rotate_figure_ccw(False)
       tmp = self.figure
       self.figure = self.next_figure
       self.next_figure = tmp
       self.px=self.bw / 2 - 2 #+ random.randint(-3, 3) #-len(figure.split('\n')[0])/2
       self.py=self.bh - 3
       if self.figure is None: 
           self.new_figure()
       else:
           self.queue_draw_next()

    def rotate_figure_cw(self, check_fit):
       oldfigure = copy.deepcopy(self.figure)
       for i in range(4):
          for j in range(4):
             self.figure[i][j]=oldfigure[j][3-i]
       if not check_fit or self.figure_fits(): return True
       else:
          self.figure=oldfigure
          return False
    
    def rotate_figure_ccw(self, check_fit):
       oldfigure = copy.deepcopy(self.figure)
       for i in range(4):
          for j in range(4):
             self.figure[i][j]=oldfigure[3-j][i]
       if not check_fit or self.figure_fits(): return True
       else:
          self.figure=oldfigure
          return False
        
    def drop_figure(self):
       oldy = self.py
       self.py-=1
       while self.figure_fits(): self.py -= 1
       self.py+=1
       return oldy!=self.py 

    def figure_fits(self):
       for i in range(4):
          for j in range(4):
             if self.figure[i][j] != 0:
               if i+self.py<0 or j+self.px<0 or j+self.px>=self.bw: return False
               if i+self.py<self.bh: 
                    if self.glass[i+self.py][j+self.px] != 0: return False
       return True 

    def put_figure(self):
       self.score += self.figure_score
       self.queue_draw_score()
       for i in range(4):
          for j in range(4):
             if i+self.py<self.bh and self.figure[i][j] != 0: self.glass[i+self.py][j+self.px]=self.figure[i][j]
    
    def chk_glass(self):
       clearlines = []
       for i in range(self.bh-1, -1, -1):
          j = 0
          while j<self.bw and self.glass[i][j]!=0: j+=1
          if j>=self.bw:
             clearlines.append(i)
             self.linecount+=1
             for j in range(self.bw):
                self.glass[i][j] = -self.glass[i][j]
       if len(clearlines)>0:         
          self.make_sound('boom.au')
          for i in clearlines:
             for j in range(self.bw): self.glass[i][j] = 0
          self.queue_draw_glass(True)
          time.sleep(self.time_step)
          self.next_tick+=self.time_step*2
       for i in clearlines:
          tmp = self.glass[i]
          for ii in range(i, self.bh-1):
             self.glass[ii] = self.glass[ii+1]
          self.glass[self.bh-1] = tmp
        
    def draw_background(self, cairo_ctx):
       cairo_ctx.set_source_rgb(self.color_back.red,
                                self.color_back.green,
                                self.color_back.blue)
       cairo_ctx.rectangle(0, 0, self.window_w, self.window_h)
       cairo_ctx.fill()
       cairo_ctx.set_source_rgb(self.color_glass.red,
                                self.color_glass.green,
                                self.color_glass.blue)
       cairo_ctx.rectangle(self.xshift-self.bwpx/2, self.yshift, self.bwpx*(self.bw+1), self.bhpx*self.bh+self.bhpx/2)
       cairo_ctx.fill()
    
    def expose_cb(self, widget, event):
       cairo_ctx = widget.get_window().cairo_create()
       self.update_picture(cairo_ctx) 
       return True

    def queue_draw_complete(self):
        self.queue_draw_score()
        self.queue_draw_next()
        self.queue_draw_glass(True)
        self.window.queue_draw()
     
    def queue_draw_score(self):
        self.window.queue_draw_area(0, 0, self.xshift-self.bw*2, self.window_h)

    def queue_draw_next(self):
        self.window.queue_draw_area(self.xnext, self.ynext, self.bwpx*5, self.bhpx*5 + 50)

    def queue_draw_glass(self, redraw):
       if redraw:
           self.window.queue_draw_area(self.xshift-self.bwpx/2, self.yshift, self.bwpx*(self.bw+1), self.bhpx*self.bh+self.bhpx/2)
       else:
           # TODO: Only update the block since nothing else changed
           self.window.queue_draw_area(self.xshift-self.bwpx/2, self.yshift, self.bwpx*(self.bw+1), self.bhpx*self.bh+self.bhpx/2)

    def update_picture(self, cairo_ctx):
        self.view_glass=None   
        self.draw_background(cairo_ctx)
        self.draw_score(cairo_ctx)

        self.draw_glass(cairo_ctx)
        if self.game_mode is self.GAME_OVER: self.draw_game_end_poster(cairo_ctx)
        if self.game_mode is self.SELECT_LEVEL: self.draw_select_level_poster(cairo_ctx)
       
        self.draw_next(cairo_ctx)

    
    def keypress_cb(self, widget, event):
       self.key_action(Gdk.keyval_name(event.keyval))
       return True

    def keyrelease_cb(self, widget, event):
       return True

    def timer(self):
        while self.game_mode == self.PLAY and time.time() >= self.next_tick:
            self.next_tick += self.time_step
            self.tick()  
        if self.game_mode != self.PLAY:
            self.next_tick = time.time()+100
        return True

    def draw_string(self, cairo_ctx, string, x, y, is_center):
        pl = PangoCairo.create_layout(cairo_ctx)
        pl.set_text(string, -1)
        pl.set_font_description(self.scorefont)
        width = pl.get_size()[0]/Pango.SCALE

        if is_center:
            x = x - width / 2
 
        cairo_ctx.move_to(int(x), int(y))
        PangoCairo.layout_path(cairo_ctx, pl)
    
    def draw_game_end_poster(self, cairo_ctx):
        cairo_ctx.set_source_rgb(self.colors[0].red,
                                 self.colors[0].green,
                                 self.colors[0].blue)
        cairo_ctx.rectangle(self.xshift, self.yshift+(self.bh/2-3)*self.bhpx, self.bw*self.bwpx, 6*self.bhpx)
        cairo_ctx.fill()
        cairo_ctx.set_source_rgb(self.color_score.red,
                                 self.color_score.green,
                                 self.color_score.blue)
        self.draw_string(cairo_ctx, 'GAME OVER', self.xshift+(self.bwpx*self.bw)/2, self.yshift+(self.bh/2-1)*self.bhpx, True)    
        self.draw_string(cairo_ctx, 'Again? (x/o)', self.xshift+(self.bwpx*self.bw)/2, self.yshift+(self.bh/2+1)*self.bhpx, True)    
        cairo_ctx.fill()   
 
    def draw_score(self, cairo_ctx):
        displaystr = 'Score: ' + str(self.score)
        displaystr += '\nLevel: ' + str(self.level)
        displaystr += '\nLines: ' + str(self.linecount)

        cairo_ctx.set_source_rgb(self.color_score.red,
                                 self.color_score.green,
                                 self.color_score.blue)
        self.draw_string(cairo_ctx, displaystr, self.scorex, self.scorey, False)
        cairo_ctx.fill()
    
    def set_level(self, new_level):    
        self.level = new_level
        if self.level < 0: self.level = 0
        if self.level > 9: self.level = 9
        self.time_step = 0.1 + (9-self.level)*0.1
        self.next_tick = time.time()+self.time_step
    
    def draw_select_level_poster(self, cairo_ctx):    
        cairo_ctx.set_source_rgb(self.colors[0].red,
                                 self.colors[0].green,
                                 self.colors[0].blue)
        cairo_ctx.rectangle(self.xshift, self.yshift+(self.bh/2-3)*self.bhpx, self.bw*self.bwpx, 7*self.bhpx)
        cairo_ctx.fill()

        cairo_ctx.set_source_rgb(self.color_score.red,
                                 self.color_score.green,
                                 self.color_score.blue)
       
        self.draw_string(cairo_ctx, 'SELECT', self.xshift+(self.bwpx*self.bw)/2, self.yshift+(self.bh/2-2)*self.bhpx, True)    
        self.draw_string(cairo_ctx, 'LEVEL: '+str(self.level), self.xshift+(self.bwpx*self.bw)/2, self.yshift+(self.bh/2)*self.bhpx, True)    
        self.draw_string(cairo_ctx, 'enter to start', self.xshift+(self.bwpx*self.bw)/2, self.yshift+(self.bh/2+2)*self.bhpx, True)    
        cairo_ctx.fill()

    def clear_glass(self):
        for i in range(self.bh):
           for j in range(self.bw):
              self.glass[i][j]=0

    def init_game(self):
#    print 'Init Game'
        self.clear_glass()
        self.complete_update = True
        self.glass_update = True
        self.linecount = 0
        self.score = 0
        self.new_figure()
        self.set_level(5)
 
        self.queue_draw_complete()
        self.game_mode = self.SELECT_LEVEL
    
    def csconnect(self):
        if self.cssock!=None:
            self.cssock.close()
        self.cssock = socket.socket()
        self.sound = False
        if self.cssock: 
            try:
                self.cssock.connect(('127.0.0.1', 6783))
#            print "Connected to csound server"
                self.sound = True
                msg = "csound.SetChannel('sfplay.%d.on', 1)\n" % self.csid
                self.cssock.send(msg)         
            except:
                self.cssock.close()
                print "Sound server does not respond "
                return
               

    def draw_next(self, cairo_ctx):
        cairo_ctx.set_line_width(1)
        cairo_ctx.set_source_rgb(0, 
                                 0, 
                                 0)

        self.draw_string(cairo_ctx, 'NEXT', self.xnext+self.bwpx*2.5, self.ynext, True)    
        cairo_ctx.fill()
        cairo_ctx.set_source_rgb(self.colors[0].red, 
                                 self.colors[0].green, 
                                 self.colors[0].blue);
        cairo_ctx.rectangle(self.xnext, self.ynext+50, self.bwpx*5, self.bhpx*5)
        cairo_ctx.fill() 
        for i in range(4):
            for j in range(4):
                if self.next_figure[i][j] is not 0:
                    color = self.colors[self.next_figure[i][j]]
                    cairo_ctx.set_source_rgb(color.red, color.green, color.blue)
	            cairo_ctx.rectangle(self.xnext+j*self.bwpx+self.bwpx/2, self.ynext+50+(3-i)*self.bhpx+self.bhpx/2, self.bwpx, self.bhpx)
        cairo_ctx.fill()

        
    def make_sound(self,filename):
        if self.sound and self.soundon:
            msg = "perf.InputMessage('i 108 0 3 \"%s\" %d 0.7 0.5 0')\n" % (os.path.abspath(filename), self.csid)
            self.cssock.send(msg)

    def mousemove_cb(self, win, event):
        print "Ah!"
        return True

    def __init__(self, canvas):
        self.glass=[[0]*self.bw for i in range(self.bh)]
        self.view_glass=None
        self.window = canvas

        # remove any children of the window that Sugar may have added
        # for widget in self.window.get_children():
        #     self.window.remove(widget)

        self.window_w = self.window.get_screen().get_width()
        self.window_h = self.window.get_screen().get_height()
#        print self.window_w, "x", self.window_h
#        if self.window_w > 1200: self.window_w=1200
#        if self.window_h > 900: self.window_h=900
        # self.window.set_title("Block Party")
        self.window.connect("destroy", lambda w: Gtk.main_quit())
        self.window.set_size_request(self.window_w, self.window_h)
        self.window.connect("draw", self.expose_cb)
        self.window.connect("key_press_event", self.keypress_cb)
        self.window.connect("key_release_event", self.keyrelease_cb)
        self.window.show()
        # area = self.window.window
#    area.set_cursor(invisible)
        self.color_back = Color(Gdk.Color.parse("white")[1])
        self.color_glass = Color(Gdk.Color.parse("grey")[1])
        self.color_score = Color(Gdk.Color.parse("grey26")[1])
        self.bwpx=int(self.window_w/(self.bw+self.bw/2+2))
        self.bhpx=int(self.window_h/(self.bh+2))
        if self.bwpx < self.bhpx: self.bhpx = self.bwpx
        else: self.bwpx = self.bhpx
        self.xshift = int((self.window_w - (self.bw+1)*self.bwpx) / 2)
        self.yshift = int((self.window_h - (self.bh+1)*self.bhpx) / 2)
        self.xnext = self.xshift + (self.bw+3)*self.bwpx
        self.ynext = self.yshift
        for i in range(len(self.colors)):
            self.colors[i] = Color(Gdk.Color.parse(self.colors[i])[1])
        self.scorefont = Pango.FontDescription('Sans')
        self.scorefont.set_size(self.window_w*14*Pango.SCALE/1024)
        self.csconnect()
        GObject.timeout_add(20, self.timer)
        self.init_game()

def main():
    win = Gtk.Window(Gtk.WINDOW_TOPLEVEL)
    t = BlockParty(win)
    Gtk.main()
    return 0

if __name__ == "__main__":
    main()

