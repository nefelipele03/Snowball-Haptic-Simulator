# -*- coding: utf-8 -*-
import sys
import numpy as np
import pygame
import math
from Physics import Physics
from Graphics import Graphics

class Start:
    print("yahoooo")


class PA:
    def __init__(self):
        self.physics = Physics(hardware_version=2)
        self.device_connected = self.physics.is_device_connected()
        self.graphics = Graphics(self.device_connected)

        xc, yc = self.graphics.screenVR.get_rect().center

        self.x_ball = xc
        self.y_ball = yc

        self.R = 60.0
        self.R_max = 130.0
        self.offset = 40
        self.k = -self.R / 15
        self.b = 0.003

        self.prev_xh = None
        self.v_filtered = np.array([0.0, 0.0])
        self.alpha_v = 0.2
        self.prev_force_engaged = False

        self.align_tol = 4.0
        self.inward_speed_tol = 0.0
        self.preload_scale = 1.0
        self.max_preload_pixels = 200.0
        self.mouse_k = 0.5
        self.mouse_b = 0.6

        self.radius_growth_gain = 0.1
        self.radius_increase_speed_threshold = 20.0

        # visualization variables
        self.ball_position_x = 300
        self.ball_position_y = 200
        self.ball_radius = 20
        self.prev_ball_position_x = 300
        self.prev_ball_position_y = 200
        self.prev_ball_radius = 20

        self.trail_positions = [] #holds the positions of where the field ball has been
        self.trail_colour = [] #holds how many times that position has been visited to adjust the colour
        self.motion_dir  = np.array([0.0, 0.0])

        self.dot1_position_x, self.dot1_position_y = 305, 210
        # self.dot2_position_x, self.dot2_position_y = 315, 198
        # self.dot3_position_x, self.dot3_position_y = 295, 195
        # self.dot4_position_x, self.dot4_position_y = 290, 205
        # self.dot5_position_x, self.dot5_position_y = 285, 198

    def run(self):
        p = self.physics
        g = self.graphics

        keyups, xm = g.get_events()

        if self.device_connected:
            pA0, pB0, pA, pB, pE = p.get_device_pos()
            pA0, pB0, pA, pB, xh = g.convert_pos(pA0, pB0, pA, pB, pE)
        else:
            xh = g.haptic.center
            pA0 = pB0 = pA = pB = xh

        fe = np.array([0.0, 0.0])
        xh = np.array(xh, dtype=float)

        g.erase_screen()

        for key in keyups:
            if key == ord("q"):
                sys.exit(0)
            if key == ord("m"):
                pygame.mouse.set_visible(not pygame.mouse.get_visible())
            if key == ord("r"):
                g.show_linkages = not g.show_linkages
            if key == ord("d"):
                g.show_debug = not g.show_debug

            # Field visualization
            # -------------------------------

            times_visited_position = sum(
                1 for x, y, r, col in self.trail_positions if x == self.ball_position_x and y == self.ball_position_y)
            if times_visited_position == 0:  # the area becomes light green
                self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius, g.cGreen3])
            elif times_visited_position == 1:  # the area becomes a bit more green
                self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius, g.cGreen2])
            else:
                self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius,
                                             g.cGreen1])  # the area is fully cleaned out


            #MOTION OF FIELD BALL ROLLING WITH HAPTICS
            #---------------------------------------
            # motion_mag_ball = 0 #magnitude in big ball pixels
            # self.motion_dir = #some unit vector showing direction of motion
            #
            # scale_factor = 3
            # motion_mag_field = motion_mag_ball/scale_factor #motion in the field in pixels
            # motion_field_pixels = motion_mag_field * self.motion_dir #motion in the field in each direction in pixels
            # self.ball_position_x += motion_field_pixels[0] #adding the motion to the existing position x
            # self.ball_position_y += motion_field_pixels[1] #adding the motion to the existing position y
            # self.dot1_position_x += self.ball_position_x * 1.2 #moving the dot by the same direction, a bit faster to show roll
            # self.dot1_position_y += self.ball_position_y *1.2  #moving the dot by the same direction, a bit faster to show roll

            #DOT TO SIMULATE ROLLING (just one for now, not tested)
            # bx, by, br = self.ball_position_x, self.ball_position_y, self.ball_radius #rename big circle variables
            # sx, sy, sr = self.dot1_position_x, self.dot1_position_y, 1  # rename small circle variables
            # distance = math.hypot(sx - bx, sy - by) #calculate the distance between the centers
            # if distance + sr > br: #dot not in view anymore
            #     self.dot1_position_x, self.dot1_position_y = -self.motion_dir * self.ball_radius #if it starts being outside the radius, sends it back to the beginning of the circle in the opposite direction of motion


            # MOTION OF FIELD BALL ROLLING WITH KEYS
            if key == ord('a'):
                # self.trail_positions.append([, self.ball_position_y, self.ball_radius])
                self.ball_radius += 5
                print("self.ball_radius", self.ball_radius)
            if key == ord('s'):
                # self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius])
                self.ball_position_x += 5
                print("self.ball_position_x", self.ball_position_x)
                self.dot1_position_x +=7

            if key == ord('w'):
                # self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius])
                self.ball_position_x -= 5
                self.dot1_position_x -= 7
                print("self.ball_position_x", self.ball_position_x)
            if key == ord('f'):
                # self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius])
                self.ball_position_y += 5
                self.dot1_position_y += 7
                print("self.ball_position_y", self.ball_position_y)
            if key == ord('g'):
                # self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius])
                self.ball_position_y -= 5
                self.dot1_position_y -= 7
                print("self.ball_position_y", self.ball_position_y)
            # ----------------------------------


        x_tool = xh[0]
        y_tool = xh[1]

        dx = x_tool - self.x_ball
        dy = y_tool - self.y_ball
        direction = np.array([0.0, 0.0])

        norm_ball = np.sqrt(dx**2 + dy**2)
        dist_from_ball_outline = norm_ball - self.R

        if norm_ball > 1e-9:
            direction = np.array([dx, dy]) / norm_ball

        if self.prev_xh is None:
            velocity = np.array([0.0, 0.0])
            self.v_filtered = np.array([0.0, 0.0])
        else:
            dt = 1.0 / g.FPS
            velocity = (xh - self.prev_xh) / dt
            self.v_filtered = self.alpha_v * velocity + (1.0 - self.alpha_v) * self.v_filtered

        if norm_ball <= self.R:
            strength = self.k * (norm_ball / self.R)
        elif norm_ball <= self.R + self.offset:
            strength = self.k * (1 - dist_from_ball_outline / self.offset)
        else:
            strength = 0.0

        spring_force = strength * direction

        if norm_ball <= self.R + self.offset and norm_ball > 1e-9:
            v_radial = np.dot(self.v_filtered, direction)
            damping_force = -self.b * v_radial * direction
        else:
            v_radial = 0.0
            damping_force = np.array([0.0, 0.0])

        dt = 1.0 / g.FPS
        inside_main_circle = norm_ball <= self.R
        moving_inward_fast_enough = v_radial < -self.radius_increase_speed_threshold

        if inside_main_circle and moving_inward_fast_enough:
            inward_step = -v_radial * dt
            self.R += self.radius_growth_gain * inward_step
            self.R = min(self.R, self.R_max)
            self.k = -self.R / 15

        force_engaged = (v_radial < 0.0)

        if force_engaged:
            fe = spring_force + damping_force
            ball_color = (0, 255, 0)
        else:
            fe = np.array([0.0, 0.0])
            ball_color = (255, 0, 0)

        new_ball_radius = int(self.R + self.offset / 2)
        pygame.draw.circle(g.screenVR, ball_color, (int(self.x_ball), int(self.y_ball)), new_ball_radius, 0)
        pygame.draw.circle(g.screenVR, (255, 255, 255), (int(self.x_ball), int(self.y_ball)), int(self.R + self.offset / 2), 2)

        # FIELD VISUALIZATION
        # -------------------------------

        self.ball_radius = new_ball_radius/3

        # times_visited_position = sum(1 for x, y, r, col in self.trail_positions if x == self.ball_position_x and y == self.ball_position_y)
        # if times_visited_position == 0:  # the area becomes light green
        #     self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius, g.cGreen3])
        # elif times_visited_position == 1:  # the area becomes a bit more green
        #     self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius, g.cGreen2])
        # else:
        #     self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius, g.cGreen1])  # the area is fully cleaned out


        for i in range(len(self.trail_positions)):
            pygame.draw.circle(g.screenField, self.trail_positions[i][3], (self.trail_positions[i][0], self.trail_positions[i][1]), self.trail_positions[i][2])

        pygame.draw.circle(g.screenField, g.cIce, [self.ball_position_x, self.ball_position_y], self.ball_radius, 0)
        pygame.draw.circle(g.screenField, g.cBlack, [self.dot1_position_x, self.dot1_position_y], 1, 0)


        self.prev_ball_position_x = self.ball_position_x
        self.prev_ball_position_y = self.ball_position_y
        self.prev_ball_radius = self.ball_radius
        #------------------------

        #VISUALIZATION OF EXPERIMENT 1
        if g.task3 == True:
            for i in range(len(self.trail_positions)):
                pygame.draw.circle(g.screenReference, self.trail_positions[i][3],  (self.trail_positions[i][0], self.trail_positions[i][1]), self.trail_positions[i][2])

            pygame.draw.circle(g.screenReference, g.cIce, [self.ball_position_x, self.ball_position_y], self.ball_radius, 0)
            pygame.draw.circle(g.screenReference, g.cIce, [self.ball_position_x, self.ball_position_y], self.ball_radius, 0)
            pygame.draw.circle(g.screenReference, g.cBlack, [self.dot1_position_x, self.dot1_position_y], 1, 0)


        self.prev_xh = xh.copy()

        if self.device_connected:
            p.update_force(fe)
        else:
            xm_vec = np.array(xm, dtype=float)
            mouse_tool_vec = xm_vec - xh
            mouse_aligned = np.linalg.norm(mouse_tool_vec) <= self.align_tol

            just_disengaged = self.prev_force_engaged and not force_engaged
            inward_reentry_case = (
                norm_ball < self.R + self.offset
                and mouse_aligned
                and v_radial < -self.inward_speed_tol
                and np.linalg.norm(fe) > 1e-9
            )

            if just_disengaged:
                pygame.mouse.set_pos((int(round(xh[0])), int(round(xh[1]))))
                xm = (float(xh[0]), float(xh[1]))
            elif inward_reentry_case:
                scale = g.window_scale / 1e3
                preload_pixels = self.preload_scale * scale * np.linalg.norm(fe) / self.mouse_k
                preload_pixels = min(preload_pixels, self.max_preload_pixels)

                preload_dir = fe / np.linalg.norm(fe)
                xm_target = xh + preload_pixels * preload_dir

                pygame.mouse.set_pos((int(round(xm_target[0])), int(round(xm_target[1]))))
                xm = (float(xm_target[0]), float(xm_target[1]))

            xh = g.sim_forces(xh, fe, xm, mouse_k=self.mouse_k, mouse_b=self.mouse_b)
            pos_phys = g.inv_convert_pos(xh)
            pA0, pB0, pA, pB, pE = p.derive_device_pos(pos_phys)
            pA0, pB0, pA, pB, xh = g.convert_pos(pA0, pB0, pA, pB, pE)

        self.prev_force_engaged = force_engaged

        g.render(pA0, pB0, pA, pB, xh, fe, xm)

    def close(self):
        self.graphics.close()
        self.physics.close()


if __name__ == "__main__":
    pa = PA()
    try:
        while True:
            pa.run()
    finally:
        pa.close()