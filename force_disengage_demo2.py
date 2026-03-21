# -*- coding: utf-8 -*-
import sys
import numpy as np
import pygame

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

        self.R = 120
        self.offset = 50
        self.k = -10
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

        force_engaged = (v_radial < 0.0)

        if force_engaged:
            fe = spring_force + damping_force
            ball_color = (0, 255, 0)
        else:
            fe = np.array([0.0, 0.0])
            ball_color = (255, 0, 0)

        pygame.draw.circle(g.screenVR, ball_color, (int(self.x_ball), int(self.y_ball)), int(self.R), 0)
        pygame.draw.circle(g.screenVR, (255, 255, 255), (int(self.x_ball), int(self.y_ball)), int(self.R), 2)

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