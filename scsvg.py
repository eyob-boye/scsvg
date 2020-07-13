#-------------------------------------------------------------------------------
# Copyright (C) 07/2020 Eyob Demissie
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in 
# the Software without restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THETHE AUTHORS OR 
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 
# Except as contained in this notice, the name(s) of the above copyright holders 
# shall not be used in advertising or otherwise to promote the sale, use or other
# dealings in this Software without prior written authorization.
#-------------------------------------------------------------------------------
"""
Simulate a State Chart drawn in SVG format (presently works with
an SVG exported from UmLet application)
"""
import sys
import itertools
import collections
import random
import re
import math
from functools import cmp_to_key

from PySide2.QtSvg import QSvgWidget
from PySide2.QtCore import QByteArray

import pysvg.core
import pysvg.shape
import pysvg.text
import pysvg.parser


#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class DiagramPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class DiagramCircle:
    def __init__(self, x, y, r):
        """Given the center coordinate and radious, create a circle."""
        self.center = DiagramPoint(x, y)
        self.radius = r

    def encloses(self, pb):
        """ Check if the given point or box or is inside this circle including the
        perimeter."""
        if isinstance(pb, DiagramPoint):
            dx = (pb.x - self.center.x)
            dy = (pb.y - self.center.y)
            d = (dx*dx + dy*dy)
            if(d <= self.radius*self.radius):
                return True
            else:
                return False
        else:
            return False

    def is_on_perimeter(self, p):
        """ Check if the given point is on the perimeter of this circle."""
        dx = (p.x - self.center.x)
        dy = (p.y - self.center.y)
        d =  (self.radius*self.radius) - (dx*dx + dy*dy)
        if(abs(d) <= 2):
            return True
        else:
            return False
        return False

    def is_attached(self, p):
        """ Check if the given point is attached to this circle."""
        return self.is_on_perimeter(p) or self.encloses(p)


#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class DiagramBox:
    def __init__(self, x, y, w, h, rotation_angle = 0):
        """Given upper left corner cooridinate point,width & height,
        initialize the perimeter points of the box."""
        self.p_ul = DiagramPoint(x, y)
        self.p_ur = DiagramPoint(x+w, y)
        self.p_bl = DiagramPoint(x, y+h)
        self.p_br = DiagramPoint(x+w, y+h)
        self.rotation_angle = rotation_angle

    def _get_rotated(self, p):
        x = p.x - self.p_ul.x
        y = p.y - self.p_ul.y
        p_x = x*math.cos(self.rotation_angle) - y*math.sin(self.rotation_angle)
        p_y = x*math.sin(self.rotation_angle) + y*math.cos(self.rotation_angle)
        p_x = p_x + self.p_ul.x
        p_y = p_y + self.p_ul.y
        return DiagramPoint(p_x, p_y)

    def _encloses_point(self, p):
        #p_r = self._get_rotated(p)
        if ((self.p_ul.x <= p.x <=  self.p_br.x) and
            (self.p_ul.y <= p.y <=  self.p_br.y)):
            return True
        else:
            return False

    def encloses(self, pbc):
        """ Check if the given point or box or circle is inside this box
        including the perimeter."""
        if isinstance(pbc, DiagramPoint):
            pbc_r = self._get_rotated(pbc)
            return self._encloses_point(pbc_r)
        elif isinstance(pbc, DiagramBox):
            p_ul_r = self._get_rotated(pbc.p_ul)
            p_br_r = self._get_rotated(pbc.p_br)
            return self._encloses_point(p_ul_r) and self._encloses_point(p_br_r)
        elif isinstance(pbc, DiagramCircle):
            p1 = self._get_rotated(DiagramPoint(pbc.center.x, pbc.center.y-pbc.radius))
            p2 = self._get_rotated(DiagramPoint(pbc.center.x, pbc.center.y-pbc.radius))
            p3 = self._get_rotated(DiagramPoint(pbc.center.x-pbc.radius, pbc.center.y))
            p4 = self._get_rotated(DiagramPoint(pbc.center.x-pbc.radius, pbc.center.y))
            return (self._encloses_point(p1) and
                    self._encloses_point(p2) and
                    self._encloses_point(p3) and
                    self._encloses_point(p4))
        else:
            return False

    def is_on_perimeter(self, p):
        """ Check if the given point is on the perimeter of this box."""
        p_r = self._get_rotated(p)
        if p_r != p:
            pass
        if ( (abs(p_r.y - self.p_ul.y) <= 2 and (self.p_ul.x <= p_r.x <=  self.p_br.x)) or
             (abs(p_r.y - self.p_br.y) <= 2 and (self.p_ul.x <= p_r.x <=  self.p_br.x)) or
             (abs(p_r.x - self.p_ul.x) <= 2 and (self.p_ul.y <= p_r.y <=  self.p_br.y)) or
             (abs(p_r.x - self.p_br.x) <= 2 and (self.p_ul.y <= p_r.y <=  self.p_br.y))
        ):
            return True
        else:
            return False
        return False

    def is_attached(self, p):
        """ Check if the given point is attached to this box."""
        return self.is_on_perimeter(p)


def pysvg_getSubElements(element):
    sub_elements = []
    for sub_element in element.getAllElements():
        if isinstance(sub_element, pysvg.core.TextContent):
            sub_element_XML = sub_element.getXML().strip()
            if sub_element_XML:
                sub_elements.append(sub_element)
        else:
            sub_elements.append(sub_element)
    return sub_elements


def translate(x,y):
    return (x,y)


class State():
    INIT_NAME = "_0_"
    BRANCH_NAME = "_B_"
    HISTORY_NAME = "_H_"

    def __init__(self, name, svg_shape, svg_shape_transform=[]):
        self.name = name
        #print(self.name)
        self.svg_shape = svg_shape
        self.svg_shape_transform = svg_shape_transform
        self.sub_states = []
        self.parent_states = []
        self.init_states = []
        self.out_transitions = []
        self.all_out_transitions = []
        self.level = 0

        if(isinstance(self.svg_shape, pysvg.shape.Rect)):
            # Given upper left corner coordinate point,width & height,
            # initialize the perimeter points of the box.
            x = float(self.svg_shape.get_x())
            y = float(self.svg_shape.get_y())
            h = float(self.svg_shape.get_height())
            w = float(self.svg_shape.get_width())
            for t in self.svg_shape_transform:
                tx,ty = eval(t)
                #print("TRANSFORMS: %s,%s" % (tx,ty))
                x += tx
                y += ty
            print("[State: %s] x,y,h,w: %s,%s,%s,%s" % (self.name, x,y,h,w))
            self.shape = DiagramBox(x,y,w,h)
        elif(isinstance(self.svg_shape, pysvg.shape.Polygon)):
            points = self.svg_shape.get_points()
            points = [float(p.strip()) for p in points.strip().split(" ")]
            if len(points) == 8:
                #Then assume a rectangle polygon i.e. a branch pseudo state.
                x = points[0]
                y = points[1]
                w = math.sqrt((points[2]-points[0])**2 + (points[3]-points[1])**2)
                h = math.sqrt((points[4]-points[2])**2 + (points[5]-points[3])**2)
                rotation_angle = math.atan((points[3]-points[1]) / (points[2]-points[0]))
                for t in self.svg_shape_transform:
                    tx,ty = eval(t)
                    #print("TRANSFORMS: %s,%s" % (tx,ty))
                    x += tx
                    y += ty
                print("[State: %s] x,y,h,w,rotation: %s,%s,%s,%s,%s" % (self.name, x,y,h,w,-rotation_angle))
                self.shape = DiagramBox(x,y,w,h,-rotation_angle)
            else:
                print("Found an known polygon shape: %s" % points)
                sys.exit(1)

        elif(isinstance(self.svg_shape, pysvg.shape.Circle)):
            cx = float(self.svg_shape.get_cx())
            cy = float(self.svg_shape.get_cy())
            r = float(self.svg_shape.get_r())
            for t in self.svg_shape_transform:
                tx,ty = eval(t)
                #print("TRANSFORMS: %s,%s" % (tx,ty))
                cx += tx
                cy += ty
            print("[State: %s] x,y,r: %s,%s,%s" % (self.name, cx,cy,r))
            self.shape = DiagramCircle(cx,cy,r)
        else:
            print("Unknown shape!")
            sys.exit(1)


    def levelize(self, level=None):
        """ Set the nesting level of this state and its children in recursive manner.
        """
        if level == None:
            self.level = 0
            for s in self.sub_states:
                s.levelize(0)
            return

        self.level = level
        for s in self.sub_states:
            s.levelize(self.level+1)


    def select_sub_states(self, states):
        """Given a list of states, update this state's sub-states.
        """
        # 1. Find all the states this state encloses
        sub_states1 = []
        for s in states:
            if s == self:
                continue
            if self.shape.encloses(s.shape):
                sub_states1.append(s)

        # 2. Find the immediate sub states of this state.
        # 2.1 From the identified enclosed states, find the ones
        #     that are enclosed by another one.
        sub_states2 = itertools.permutations(sub_states1,2)
        sub_sub_states = set()
        for (s1,s2) in sub_states2:
            if s1.shape.encloses(s2.shape):
                sub_sub_states.add(s2)
        # 2.2 Select only the immediate sub-states.
        for s in sub_states1:
            if s not in sub_sub_states:
                self.sub_states.append(s)
                # If the substate is an init substate put in special list as well
                if s.name == State.INIT_NAME:
                    self.init_states.append(s)

    def select_parent_states(self, states):
        """Given a list of states, update this state's parent state.
        """
        # 1. Find all the states that enclose this state
        parent_states1 = []
        for s in states:
            if s == self:
                continue
            if s.shape.encloses(self.shape):
                parent_states1.append(s)
        # Sort the list in such a way immediate parent, grand parent, great grand parent, etc..
        parent_states2 = sorted(parent_states1, key =cmp_to_key(lambda s1, s2: -1 if (s1.shape.encloses(s2.shape)) else 1))
        self.parent_states = parent_states2

    def add_out_transitions(self, t):
        self.out_transitions.append(t)

    def find_all_out_transitions(self):
        """ Assuming that this state knows its parents and its own transitions,
        build a list of all transitions that can make this state exist.
        """
        # Collect all applicable out transitions on order of priority
        # highest priority is the outer most state
        for ps in reversed(self.parent_states):
            for t in ps.out_transitions:
                self.all_out_transitions.append(t)
        for t in self.out_transitions:
            self.all_out_transitions.append(t)

    def __repr__(self):
        #fmt1 = "State: %s sub-states %s parent-states %s"
        #result =  fmt1 % (self.name,
        #                  ["%s" % ss.name for ss in self.sub_states],
        #                  ["%s" % ps.name for ps in self.parent_states])

        result = self.name
        #if self.parent_states and (not self.sub_states):
        #    result = ".".join([p.name for p in reversed(self.parent_states)])+"."+result
        if self.parent_states:
            result = self.parent_states[0].name + "." + result
        return result

    def highlight(self, color):
        self.svg_shape.set_stroke(color)


def find_state(element, transform=[]):
    found_shape = None
    found_name = None  #TODO: This needs to be a list for multiple line case...  like
    found_potential_substates = []
    for e1 in pysvg_getSubElements(element):
        if isinstance(e1, pysvg.structure.G):
            t1 = e1.get_transform()
            if not t1:
                t1 = ""
            found_potential_substates.append((e1, list(transform)+[t1]))
        elif isinstance(e1, pysvg.shape.Rect):
            found_shape = (e1, element, transform)
        elif isinstance(e1, pysvg.shape.Circle):
            found_shape = (e1, element, transform)
        elif isinstance(e1, pysvg.shape.Polygon):
            # NOTE: UMLET creates two graphics elements for one statechart
            # branch diamond symbol. One with a stroke=none, the second without
            # any stroke setting. We want the second one, so skip the first.
            if(e1.get_stroke() != u"none"):
                found_shape = (e1, element, transform)
        elif isinstance(e1, pysvg.text.Text):
            found_name = e1.getAllElements()[0].content
            found_name = (found_name.split(" "))[0]
    if found_shape and found_name:
        return (found_name, found_shape, found_potential_substates)
    elif found_shape and isinstance(found_shape[0], pysvg.shape.Circle):
        return (State.INIT_NAME, found_shape, found_potential_substates)
    elif found_shape and isinstance(found_shape[0], pysvg.shape.Polygon):
        return (State.BRANCH_NAME, found_shape, found_potential_substates)
    else:
        return (None, None, found_potential_substates)


def find_all_states(element, list_of_states=[], transform=[]):
    if isinstance(element, pysvg.structure.G):
        (name, shape, potential_substates) = find_state(element, transform)
        if name and shape:
            (shape, parent_G, t2) = shape
            list_of_states.append(State(name, shape, t2))
        for e2,t2 in potential_substates:
            list_of_states = find_all_states(e2, list_of_states, transform+t2)
    else:
        for e1 in pysvg_getSubElements(element):
            if isinstance(e1, pysvg.structure.G):
                (name, shape, potential_substates) = find_state(e1, transform)
                if name and shape:
                    (shape, parent_G, t2) = shape
                    list_of_states.append(State(name, shape, t2))
                for e2,t2 in potential_substates:
                    list_of_states = find_all_states(e2, list_of_states, transform+t2)
    return list_of_states


def transition_get_endpoints(shape):
    """ Given shape of the transition extract - end points. 
    The following for example is the shape of two segment transiion earlier
    version of UMLET.
      <line y2="50" fill="none" x1="30" clip-path="url(#clipPath27)" x2="105" y1="50"/>
      <line y2="50" fill="none" x1="105" clip-path="url(#clipPath27)" x2="180" y1="50"/>
      <line y2="44" fill="none" x1="30" clip-path="url(#clipPath27)" x2="42" y1="50"/>
      <line y2="56" fill="none" x1="30" clip-path="url(#clipPath27)" x2="42" y1="50"
      />

    The following for example is the shape of two segment transtion on the latest
    version of UMLET state chart diagram.
      <path fill="none" d="M190.5 230.5 L10.5 230.5" clip-path="url(#clipPath6)"/>
      <path fill="none" d="M10.5 230.5 L10.5 11.5" clip-path="url(#clipPath6)"/>
      <path fill="none" d="M17 22.2583 L10.5 11 L4 22.2583" clip-path="url(#clipPath6)"/>
    """
     # Decide which way to parse
    if(isinstance(shape[0], pysvg.shape.Line)):
        x1 = float(shape[-3].get_x2())
        y1 = float(shape[-3].get_y2()) #Because the last two lines define arrow shape
        x2 = float(shape[0].get_x1())
        y2 = float(shape[0].get_y1())
    else:
        d_first_seg = shape[0].get_d()
        d_arrow = shape[-1].get_d()
        d_first_seg_lst = d_first_seg.split(" ")
        x1 = float(d_first_seg_lst[0][1:])
        y1 = float(d_first_seg_lst[1])
        d_arrow_lst = d_arrow.split(" ")
        x2 = float(d_arrow_lst[2][1:])
        y2 = float(d_arrow_lst[3])

    return(x1,y1,x2,y2)
    

class Transition():
    def __init__(self, svg_shape, text, svg_shape_transform=[]):
        self.text = text
        self.svg_shape = svg_shape
        self.svg_shape_transform = svg_shape_transform

        (x1, y1, x2, y2) = transition_get_endpoints(self.svg_shape)

        for t in self.svg_shape_transform:
            tx,ty = eval(t)
            #print("TRANSFORMS: %s,%s" % (tx,ty))
            x1 += tx
            y1 += ty
            x2 += tx
            y2 += ty
        print("[%s]:x1,y1,x2,y2: %s,%s,%s,%s" % (self.text,x1,y1,x2,y2))
        self.pt1 = DiagramPoint(x1, y1)
        self.pt2 = DiagramPoint(x2, y2)
        self.pt1_state = None
        self.pt2_state = None
        # TODO: Parse self.text into trigger, guard, action
        self.trigger = self.text.strip()
        self.guard = ""
        self.action = ""

    def select_end_states(self, states):
        """Given a list of states, update this transition's end point states.
        """
        pt1_state = None
        pt2_state = None
        for s in states:
            if s.shape.is_attached(self.pt1):
                pt1_state = s
            if s.shape.is_attached(self.pt2):
                pt2_state = s
            if pt1_state and pt2_state:
                break
        if pt1_state:
            self.pt1_state = pt1_state
        else:
            print("Error transition [%s] dangling at pt1." % self.text)
            sys.exit(1)

        if pt2_state:
            self.pt2_state = pt2_state
        else:
            print("Error: transition [%s] dangling at pt2." % self.text)
            sys.exit(1)

    def __repr__(self):
        fmt1 = "Transition: %s -> %s"
        fmt2 = "\n\t  trigger=|%s|\n\t  guard=|%s|\n\t  action=|%s|"
        result =  fmt1 % (self.pt1_state.name, self.pt2_state.name)
        result += fmt2 % (self.trigger, self.guard, self.action)
        return result

    def highlight(self, color):
        for line in self.svg_shape:
            line.set_stroke(color)
        #print(self.svg_shape[0].get_x2(), self.svg_shape[0].get_y2())


def find_transition(element, transform=[]):
    found_shape = []
    found_text = []
    found_somethingelse = []
    found_potential_transitions = []
    for e1 in pysvg_getSubElements(element):
        if isinstance(e1, pysvg.structure.G):
            t1 = e1.get_transform()
            if not t1:
                t1 = ""
            found_potential_transitions.append((e1, list(transform)+[t1]))
        elif isinstance(e1, pysvg.shape.Line) or isinstance(e1, pysvg.shape.Path):
            found_shape.append(e1)
        elif isinstance(e1, pysvg.text.Text):
            found_text.append(e1.getAllElements()[0].content)
        else:
            found_somethingelse.append(e1)
    #TODO: Verify that shape has an arrow head.
    if not found_potential_transitions and found_shape and not found_somethingelse:
        return (found_shape, "\n".join(found_text), element, transform, [])
    else:
        return ([], None, element, transform, found_potential_transitions)


def find_all_transitions(element, list_of_transitions=[], transform=[]):
    if isinstance(element, pysvg.structure.G):
        (shape, guard, parent_G, t2, potential_transitions) = find_transition(element, transform)
        if shape:
            list_of_transitions.append(Transition(shape, guard, t2))
        for e2,t2 in potential_transitions:
            list_of_transitions = find_all_transitions(e2, list_of_transitions, transform+t2)
    else:
        for e1 in pysvg_getSubElements(element):
            if isinstance(e1, pysvg.structure.G):
                (shape, guard, parent_G, t2, potential_transitions) = find_transition(e1, transform)
                if shape:
                    #TODO: What should the name be?
                    list_of_transitions.append(State("?name?", shape, t2))
                for e2,t2 in potential_transitions:
                    list_of_transitions = find_all_transitions(e2, list_of_transitions, transform+t2)
    return list_of_transitions


def pysvg_main2(col="red"):
    anSVG = pysvg.parser.parse('test3b.svg')
    all_states = find_all_states(anSVG)
    for s in all_states:
        print(s.name, s.svg_shape.getXML().strip())
        if s.name == "INIT":
            s.svg_shape.set_stroke(col)
    return anSVG.getXML()


class StateChartContextDefault():
    def __init__(self):
        pass

    def eval(self, trigger=None, guard=None):
        return random.choice([True, False])


class StateChart(QSvgWidget):
    def __init__(self, svg_filename="", parent=None):
        QSvgWidget.__init__(self, parent=None)
        self.svg_filename = svg_filename
        self.svg = pysvg.parser.parse(self.svg_filename)
        self.all_states = find_all_states(self.svg)
        self.all_transitions = find_all_transitions(self.svg)
        self.top_states = []
        self.top_init_states = []
        self.current_states = []
        self.highlighted_states = []
        self.highlighted_transitions = []
        self.context_object = StateChartContextDefault()

        # Teach the Transition and State objects how they are connected
        # to each other.
        for t in self.all_transitions:
            t.select_end_states(self.all_states)
            t.pt1_state.add_out_transitions(t)
            print(t)

        for s in self.all_states:
            s.select_sub_states(self.all_states)
            s.select_parent_states(self.all_states)
            # If the state does not have a parent state then, it is a top state
            # in the diagram
            if not s.parent_states:
                self.top_states.append(s)
                if s.name == State.INIT_NAME:
                    self.top_init_states.append(s)
            print(s)

        # Teach the states their nesting level.
        for s in self.top_states:
            s.levelize(0)

        # This must run after we find all states have initialized as above.
        for s in self.all_states:
            s.find_all_out_transitions()

        # Enter the state chart through the initial states
        self.current_states = self.top_init_states

        self.highlight_states(self.current_states)
        self.highlight_transitions(self.highlighted_transitions)


    def configure(self, context_object=None, initial_states=None):
        """ Given the context object and initial states, the state chart is
        configured.
        """
        if context_object != None:
            self.context_object = context_object

        if initial_states != None:
            current_states = []
            for si in initial_states:
                for s in self.all_states:
                    s_fqun = [ps.name for ps in s.parent_states]
                    s_fqun.append(s.name)
                    s_fqun = ".".join(s_fqun)
                    if(si.strip() == s_fqun):
                        current_states.append(s)
            if current_states:
                self.current_states = current_states
                self.highlight_states(self.current_states)
                self.highlight_transitions([])
                self.refresh()


    def get_path(self, state_start, state_dest):
        """ Given two states find the path to each other. This shows the border
        crossings that have to be done to reach other. For example the following
        list is returned for the path from 's12' to 's2'
            [('exit', 's1', 's12'),
             ('exit', 'diagram', 's1'),
             ('enter', 'diagram', 's2')]
        Each tuple (x, y, z) means...
            x: are we exiting or entering z
            y: is the immediate parent of z

        """
        s0_superstates = state_start.parent_states[::-1]
        s1_superstates = state_dest.parent_states[::-1]

        common_ancestor_in_s1_idx = 0

        if s0_superstates:
            path = [('exit', s0_superstates[-1], state_start)]
        else:
            path = [('exit', None, state_start)]
        for s in reversed(s0_superstates):
            if s not in s1_superstates:
                s_idx = s0_superstates.index(s)
                if s_idx > 0:
                    path.append(('exit', s0_superstates[s_idx-1], s))
                else:
                    path.append(('exit', None, s))
            else:
                # Now we have found a common ancestor, entering starts
                common_ancestor_in_s1_idx = s1_superstates.index(s)
                s1_superstates = s1_superstates[common_ancestor_in_s1_idx:]
                break

        for s_idx, s in enumerate(s1_superstates[1:]):
            path.append(('enter', s1_superstates[s_idx], s))
        if s1_superstates:
            path.append(('enter', s1_superstates[-1], state_dest))
        else:
            path.append(('enter', None, state_dest))

        return path


    def advance_state(self, environment = {}):
        """ This state machine advances the state machine based on the truth
        values of the transitions for the current states.
        """
        # Also find the common ancestors of any combinations of the
        # current states. We need to check transitions out of these
        # common ancestors before we go into the current state transitions.
        n_current_states = len(self.current_states)
        common_ancestor_states_by_order = collections.OrderedDict()
        common_ancestor_states = set([])
        for o in reversed(range(n_current_states+1)[1:]):
            #print(o)
            s_subsets = itertools.combinations(self.current_states, o)
            for ss in s_subsets:
                common_ancestor_states_by_order[ss] = set([])
                if ss:
                    common_ancestor_states_by_order[ss] = set(ss[0].parent_states)
                for s in ss:
                    common_ancestor_states_by_order[ss] &= (set(s.parent_states) - common_ancestor_states)
                common_ancestor_states |= common_ancestor_states_by_order[ss]
        #for k in common_ancestor_states_by_order:
        #    print(k, common_ancestor_states_by_order[k])

        candidate_transitions0 = []
        candidate_destinations = []
        for k in common_ancestor_states_by_order:
            transitions = []
            for s in common_ancestor_states_by_order[k]:
                transitions += s.out_transitions
            #Evaluate each transtion... but for now select one random one.
            for t in transitions:
                if self.context_object.eval(t.trigger, t.guard):
                    candidate_transitions0.append(t)
                    candidate_destinations.append(t.pt2_state)
        #for t in candidate_transitions0:
        #    print(t)

        # As long as the current state has not taken a higher order transition
        # check its low order transitions.
        current_states_exited = []
        current_states_notexited = []
        candidate_transitions1 = []
        for s in self.current_states:
            higher_t = list(set(candidate_transitions0) & set(s.all_out_transitions))
            if(len(higher_t) == 0):
                # If the state is a init pseudo state, take the transition
                # there is no need to evalueate.
                if s.name == State.INIT_NAME:
                    candidate_transitions1.append([s,s.out_transitions[0]])
                    current_states_exited.append(s)
                    break
                # Evaluate each transtion
                for t in s.out_transitions:
                    if self.context_object.eval(t.trigger, t.guard):
                        candidate_transitions1.append([s,t])
                        current_states_exited.append(s)
                        break
            else:
                # Choose the highest order transition
                candidate_transitions1.append([s,higher_t[0]])
                current_states_exited.append(s)
        current_states_notexited = list(set(self.current_states) - set(current_states_exited))

        #for s,t in candidate_transitions1:
        #    print(s,t)

        # Need to cross check if the path of the transition from each candidate
        # moves in such a way that it causes an exit or entry of another states
        # parent. If a transitions exits s111, to s0 then s12 can be affected if
        # s1 is a parent/grandparent of s12 and s111.
        candidate_transitions1_path = collections.OrderedDict()
        candidate_transitions1_exited_states = collections.OrderedDict()
        candidate_transitions1_entered_states = collections.OrderedDict()
        for s,t in candidate_transitions1:
            candidate_transitions1_path[s] = self.get_path(s, t.pt2_state)
            candidate_transitions1_exited_states[s] = []
            candidate_transitions1_entered_states[s] = []
            for p in candidate_transitions1_path[s]:
                if p[0] == "exit":
                    candidate_transitions1_exited_states[s].append(p[2])
                elif p[0] == "enter":
                    candidate_transitions1_entered_states[s].append(p[2])

        for s,t in candidate_transitions1:
            for sstt in candidate_transitions1:
                ss,tt = sstt
                if (ss == s) or (tt == t):
                    continue
                exited_parent_states = list(set(ss.parent_states) & set(candidate_transitions1_exited_states[s]))
                entered_parent_states = list(set(ss.parent_states) & set(candidate_transitions1_entered_states[s]))
                # TODO: Adopting the transition might not be the right thing to do.
                if(entered_parent_states):
                    sstt[1] = t
                elif(exited_parent_states):
                    sstt[1] = t

        # Check if we need to transition out some states that did not have
        # explicit transitions.
        candidate_transitions1_augment = []
        current_states_exited_augment = []
        for st in candidate_transitions1:
            s,t = st
            for ss in current_states_notexited:
                if (ss == s):
                    continue
                exited_parent_states = list(set(ss.parent_states) & set(candidate_transitions1_exited_states[s]))
                entered_parent_states = list(set(ss.parent_states) & set(candidate_transitions1_entered_states[s]))
                # TODO: Adopting the transition might not be the right thing to do.
                if(entered_parent_states) or (exited_parent_states):
                    candidate_transitions1_augment.append([ss,t])
                    current_states_exited_augment.append(ss)
        candidate_transitions1 += candidate_transitions1_augment
        current_states_exited += current_states_exited_augment
        current_states_notexited = list(set(self.current_states) - set(current_states_exited))

        #for s,t in candidate_transitions1:
        #    print(s,t)

        # Need to cross check the candidate transitions before taking the
        # transitions. Take highest priority (grand parent's) if the states
        # share a common ancestory.
        for st in candidate_transitions1:
            for s,t in candidate_transitions1:
                if st[0] == s:
                    continue
                if t.pt1_state in s.parent_states:
                    st[1] = t
        candidate_transitions2 = []
        for s,t in candidate_transitions1:
            candidate_transitions2.append(t)
        candidate_transitions2 = list(set(candidate_transitions2))

        # Repeat the path calculations on the final candidates.
        candidate_transitions2_path = collections.OrderedDict()
        candidate_transitions2_exited_states = collections.OrderedDict()
        candidate_transitions2_entered_states = collections.OrderedDict()
        for s,t in candidate_transitions1:
            candidate_transitions2_path[s] = self.get_path(s, t.pt2_state)
            candidate_transitions2_exited_states[s] = []
            candidate_transitions2_entered_states[s] = []
            for p in candidate_transitions2_path[s]:
                if p[0] == "exit":
                    candidate_transitions2_exited_states[s].append(p[2])
                elif p[0] == "enter":
                    candidate_transitions2_entered_states[s].append(p[2])

        # Now highligt the out transitions
        highlighted_transitions = []
        highlighted_states1 = []
        for t in candidate_transitions2:
            s = t.pt2_state
            highlighted_transitions.append(t)
            highlighted_states1.append(s)
            #TODO: Transition action, exits actions should be performed

        # Entering a super state means we have to decide in which substate
        # we need to land. See if the entered states are init states.
        # If yes... then follow through until reaching a substate that does
        # not contain an init state.
        highlighted_states2 = []
        current_states = []
        entered_states = {}
        for ss in highlighted_states1:
            entered_states[ss] = []
            cs1 = [ss]
            while True:
                no_init_state = True
                entered_states[ss] += cs1
                cs2 = list(cs1)
                cs1 = []
                for s in cs2:
                    # if s is branch pseudo state, then take the transitions.
                    if s.name == State.BRANCH_NAME:
                        tt = None
                        for t in s.out_transitions:
                            if self.context_object.eval(t.trigger, t.guard):
                                tt = t
                                break
                        if not tt:
                            print("Warning: Branch pseudo-state did not transition out. %s" % s)
                            # If using the default context, take a random selection.
                            if(isinstance(self.context_object, StateChartContextDefault)):
                                tt = random.choice(s.out_transitions)
                        if tt:
                            highlighted_transitions.append(tt)
                            highlighted_states2.append(tt.pt2_state)
                            cs1.append(tt.pt2_state)
                        continue
                    # if s does not contain an init state then done with it.
                    if not s.init_states:
                        cs1.append(s)
                        continue
                    for init_state in s.init_states:
                        no_init_state = False
                        highlighted_states2.append(init_state)
                        for t in init_state.out_transitions:
                            highlighted_transitions.append(t)
                            highlighted_states2.append(t.pt2_state)
                            cs1.append(t.pt2_state)

                if no_init_state:
                    current_states += cs2
                    break

        # TODO: Do entry actions of states being entered.
        self.highlighted_transitions =  highlighted_transitions
        self.highlighted_states = highlighted_states1 + highlighted_states2 + current_states_notexited
        self.current_states = current_states + current_states_notexited

    def highlight_states(self, states):
        for s in self.all_states:
            if s in states:
                highlight_color = "red"
            else:
                highlight_color = "black"
            s.highlight(highlight_color)

    def highlight_transitions(self, transitions):
        for t in self.all_transitions:
            if t in transitions:
                highlight_color = "red"
            else:
                highlight_color = "black"
            t.highlight(highlight_color)

    def getSvgXML(self):
        xml = self.svg.getXML()
        # Here we scrub the text content of the XML to make
        # sure the special character < and & are properly escaped
        # pysvg does not do this for us (bug).
        xml_text_pat = re.compile(r"""<text.*?>(?P<text_data>.*?)</text\s*>""",
        re.VERBOSE | re.MULTILINE | re.UNICODE |  re.DOTALL)
        groups = xml_text_pat.findall(xml)
        text_data_to_scrub = []
        for i in range(len(groups)):
            t_data = (u"%s" % groups[i])
            if t_data:
                if "<" in t_data or "&" in t_data:
                    t_data_escaped = t_data.replace("&", "&amp;")
                    t_data_escaped = t_data_escaped.replace("<", "&lt;")
                    text_data_to_scrub.append((t_data, t_data_escaped))
        for t0, t1 in text_data_to_scrub:
            xml = xml.replace(t0, t1)
        #with open("t0.svg", "w") as ofile:
        #    ofile.write(xml)
        return xml

    def refresh(self, defaultviewsize=False):
        xml = self.getSvgXML()
        svg_ba = QByteArray(bytes(xml,'utf-8'))
        self.load(svg_ba)
        if defaultviewsize:
            #  This will make sure diagram is shown full scale.
            self.resize(self.sizeHint())

    def mousePressEvent(self, event):
        print(event.x(), event.y())
        self.advance_state()
        self.highlight_states(self.highlighted_states)
        self.highlight_transitions(self.highlighted_transitions)
        self.refresh()

