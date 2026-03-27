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
        
        self.task3_init = True

        self.R = 60.0
        self.R_max = 130.0
        self.R_min = 20
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
        self.radius_melting_gain = 0.9

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

        #ADDED
        # ball rolling variables
        self.ball_velocity = np.array([0.0, 0.0])
        self.prev_vel = 0
        self.ball_mass = 1
        self.ball_damping = 0.97
        self.force_scale = 0.01
        self.mass_scale = 0.8
        self.ball_acceleration = np.array([0.0, 0.0])

        self.flower_positions = []
        self.collision_count = 0

        self.maze_completed = False
        self.start_time_exp1 = None
        self.start_time_exp3 = None
        
        # Task 2 variables
        self.task2_stage = 0
        self.task2_target_radius = 100
        self.task2_total_trials = 5
        self.task2_current_trial = 0
        self.task2_results = []
        self.task2_finished = False
        self.task2_first_snowball_size = None
        self.task2_initial_ball_size_at_startup = int(self.R + self.offset / 2) 
        self.task2_finish_time = None

        #initialize all variables
        self.reset_experiments()
        #-----------------------------------

    def reset_experiments(self):
        """Resets all simulation and experiment variables to their starting state."""
        xc, yc = self.graphics.screenVR.get_rect().center

        self.x_ball = xc
        self.y_ball = yc
        self.R = 60.0
        self.R_max = 130.0
        self.R_min = 20
        self.offset = 40
        self.k = -self.R / 15
        self.b = 0.003

        self.prev_xh = None
        self.v_filtered = np.array([0.0, 0.0])
        self.prev_force_engaged = False

        # Visualization and Physics state
        self.ball_position_x = 300
        self.ball_position_y = 200
        self.ball_radius = 20
        self.trail_positions = []
        self.trail_colour = []
        self.ball_velocity = np.array([0.0, 0.0])
        self.ball_acceleration = np.array([0.0, 0.0])

        self.collision_count = 0
        self.maze_completed = False

        # Reset Graphics-specific flags if necessary
        self.graphics.current_collisions = 0
        # Clear the surfaces (trails)
        self.graphics.screenField.fill((0, 0, 0, 0))  # Or your background color
        self.graphics.screenReference.fill((0, 0, 0, 0))

        self.maze_completed = False
        self.start_time_exp1 = None
        self.start_time_exp3 = None

    def point_in_triangle(self, px, py, A, B, C):
        # Helper function to compute the sign
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        d1 = sign((px, py), A, B)
        d2 = sign((px, py), B, C)
        d3 = sign((px, py), C, A)

        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)

        return not (has_neg and has_pos)

        

    def reset_task2_ball_to_startup_size(self):
        self.R = max(1.0, self.task2_initial_ball_size_at_startup - self.offset / 2)
        self.k = -self.R / 15



    def run(self):
        p = self.physics
        g = self.graphics

        keyups, xm, mouse_clicks = g.get_events()

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
            #test
            if key == ord("k"):
                g.menu = False
            #------------
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

            if key == ord('x') and g.task2:
                current_size = int(self.R + self.offset / 2)

                if self.task2_stage == 0:
                    self.task2_first_snowball_size = current_size
                    self.task2_stage = 1
                    self.task2_current_trial = 0
                    self.task2_results = []
                    print("Task 2 started.")
                    print(f"Startup ball size: {self.task2_initial_ball_size_at_startup}")
                    print(f"First free snowball size: {self.task2_first_snowball_size}")

                    self.reset_task2_ball_to_startup_size()

                elif self.task2_stage == 1:
                    self.task2_results.append(current_size)
                    self.task2_current_trial += 1

                    print(f"Trial {self.task2_current_trial}/{self.task2_total_trials}")
                    print(f"Target size: {self.task2_target_radius}")
                    print(f"Achieved size: {current_size}")
                    print(f"Error: {abs(current_size - self.task2_target_radius)}")

                    if self.task2_current_trial >= self.task2_total_trials:
                        self.task2_finished = True
                        self.task2_finish_time = pygame.time.get_ticks()
                    else:
                        self.reset_task2_ball_to_startup_size()

            # ----------------------------------

        #Buttons changing colour with hovering
        if self.point_in_triangle(xm[0], xm[1], (580, 315), (580, 410), (850, 362)):
            g.exp1buttoncolour = g.cYellow
            g.exp2buttoncolour = g.cOrange
            g.exp3buttoncolour = g.cOrange
        elif self.point_in_triangle(xm[0], xm[1], (580, 415), (580, 510), (850, 462)):
            g.exp1buttoncolour = g.cOrange
            g.exp2buttoncolour = g.cYellow
            g.exp3buttoncolour = g.cOrange
        elif self.point_in_triangle(xm[0], xm[1], (580, 515), (580, 610), (850, 562)):
            g.exp1buttoncolour = g.cOrange
            g.exp2buttoncolour = g.cOrange
            g.exp3buttoncolour = g.cYellow
        else:
            g.exp1buttoncolour = g.cOrange
            g.exp2buttoncolour = g.cOrange
            g.exp3buttoncolour = g.cOrange

        if g.menu:
            # experiment 1 clicked:
            for mx, my in mouse_clicks:
                if self.point_in_triangle(mx, my, (580, 315), (580, 410), (850, 362)):
                    g.task1 = True
                    #get start time for experiment 1
                    if self.start_time_exp1 is None:
                        self.start_time_exp1 = pygame.time.get_ticks() / 1000
                    g.menu = False
                if self.point_in_triangle(mx, my, (580, 415), (580, 510), (850, 462)):
                    g.task2 = True
                    g.menu = False
                if self.point_in_triangle(mx, my, (580, 515), (580, 610), (850, 562)):
                    g.task3 = True
                    if self.start_time_exp3 is None:
                        self.start_time_exp3 = pygame.time.get_ticks() / 1000
                    g.menu = False

        if not g.menu:
            for mx, my in mouse_clicks:
                if g.home_rect.collidepoint(mx, my):
                    self.reset_experiments()
                    g.menu = True

        x_tool = xh[0]
        y_tool = xh[1]

        dx = x_tool - self.x_ball
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
            

        force_engaged = (v_radial < -3.0)

        if force_engaged:
            fe = spring_force + damping_force
            ball_color = (0, 255, 0)

            #ADDED
            # BALL DYNAMICS
            ball_force = -fe

            # acceleration
            self.ball_acceleration += ((-ball_force * self.force_scale) / (self.ball_mass * self.mass_scale))
            # print(self.ball_acceleration)

            # velocity
            self.ball_velocity = (self.ball_acceleration)  # * dt)
            # print(self.ball_velocity)
            #------------------------------------------

        else:
            fe = np.array([0.0, 0.0])
            ball_color = (255, 0, 0)

            #ADDED
            # BALL DYNAMICS
            ball_force = np.array([0.0, 0.0])

            self.ball_acceleration = np.array([0.0, 0.0])
            self.ball_velocity *= self.ball_damping

        # # pos
        # self.ball_position_x += self.ball_velocity[0]
        # self.ball_position_y += self.ball_velocity[1]

        # pos
        self.ball_position_x += self.ball_velocity[0]
        self.ball_position_y += self.ball_velocity[1]

        field_width, field_height = g.screenField.get_size()

        self.ball_position_x = max(self.ball_radius, min(self.ball_position_x, field_width - self.ball_radius))
        self.ball_position_y = max(self.ball_radius, min(self.ball_position_y, field_height - self.ball_radius))

        

        if g.task3:
            if self.task3_init:
                self.ball_position_x = 50.0
                self.ball_position_y = 50.0
                self.prev_ball_position_x = 50.0
                self.prev_ball_position_y = 50.0
                
                self.R = 45.0
                self.R_max = 55.0
                self.R_min = 40.0
                
                self.ball_damping = 0.98
                self.mass_scale = 0.8
                
                self.radius_melting_gain = 0.9999
                
                self.task3_init = False
            
            self.flower_positions = self.graphics.flower_positions

            for flower_x, flower_y in self.graphics.flower_positions:
                # distance from ball to flower
                dx = self.ball_position_x - flower_x
                dy = self.ball_position_y - flower_y
                dist = np.sqrt(dx ** 2 + dy ** 2)

                if dist < (self.R - 20):  # +10):
                    #print("hit flower")
                    self.collision_count += 1
                    self.graphics.current_collisions = self.collision_count

                    # direction towards flower (unit vector)
                    nx = (self.ball_position_x - flower_x) / dist
                    ny = (self.ball_position_y - flower_y) / dist

                    contact_dist = self.R
                    self.ball_position_x = flower_x + nx * contact_dist
                    self.ball_position_y = flower_y + ny * contact_dist

                    self.ball_velocity = np.array([0.0, 0.0])
                    self.ball_acceleration = np.array([0.0, 0.0])

            # pygame.draw.rect(g.screenReference, (0,255,0), (220,300, 60,60))
            #-----------------------------


        new_ball_radius = int(self.R + self.offset / 2)
        pygame.draw.circle(g.screenVR, ball_color, (int(self.x_ball), int(self.y_ball)), new_ball_radius, 0)
        pygame.draw.circle(g.screenVR, (255, 255, 255), (int(self.x_ball), int(self.y_ball)), int(self.R + self.offset / 2), 2)

        # FIELD VISUALIZATION
        # -------------------------------

        self.ball_radius = new_ball_radius/3

        times_visited_position = sum(1 for x, y, r, col in self.trail_positions if x == self.ball_position_x and y == self.ball_position_y)
        if times_visited_position == 0:  # the area becomes light green
            self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius, g.cGreen3])
        elif times_visited_position == 1:  # the area becomes a bit more green
            self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius, g.cGreen2])
        else:
            self.trail_positions.append([self.ball_position_x, self.ball_position_y, self.ball_radius, g.cGreen1])  # the area is fully cleaned out


        for i in range(len(self.trail_positions)):
            pygame.draw.circle(g.screenField, self.trail_positions[i][3], (self.trail_positions[i][0], self.trail_positions[i][1]), self.trail_positions[i][2])

        pygame.draw.circle(g.screenField, g.cIce, [self.ball_position_x, self.ball_position_y], self.ball_radius, 0)
        # pygame.draw.circle(g.screenField, g.cBlack, [self.dot1_position_x, self.dot1_position_y], 1, 0)

        self.prev_ball_position_x = self.ball_position_x
        self.prev_ball_position_y = self.ball_position_y
        self.prev_ball_radius = self.ball_radius
        #------------------------

        #VISUALIZATION OF EXPERIMENT 3
        if g.task3 == True:
            for i in range(len(self.trail_positions)):
                pygame.draw.circle(g.screenReference, self.trail_positions[i][3],  (self.trail_positions[i][0], self.trail_positions[i][1]), self.trail_positions[i][2])

            pygame.draw.circle(g.screenReference, g.cIce, [self.ball_position_x, self.ball_position_y], self.ball_radius, 0)
            pygame.draw.circle(g.screenReference, g.cIce, [self.ball_position_x, self.ball_position_y], self.ball_radius, 0)
            # pygame.draw.circle(g.screenReference, g.cBlack, [self.dot1_position_x, self.dot1_position_y], 1, 0)
            current_time = pygame.time.get_ticks() / 1000 #get current time at each frame
            
            if 220 <= self.ball_position_x <= 220 + 60 and 300 <= self.ball_position_y <= 300 + 60:
                # self.task1_finished = False
                print("Task 3 Trial Finished!")
                print("RESULTS")
                print("---------------------------------------------------")
                print("Using Haply: ", self.device_connected)
                print("Number of Collisions:", self.collision_count, "collisions")
                time_taken = current_time + self.start_time_exp3
                print("Time Taken:", time_taken, "seconds")
                print("---------------------------------------------------")
                sys.exit(0)
        
        # VISUALIZATION / LOGIC OF EXPERIMENT 2
        if g.task2 == True:
            if self.task2_finished and self.task2_finish_time is not None:
                if pygame.time.get_ticks() - self.task2_finish_time >= 2000:
                    print("Task 2 Finished!")
                    print("---------------------------------------------------")
                    print("Using Haply:", self.device_connected)
                    print("Target size:", self.task2_target_radius)
                    for i, result in enumerate(self.task2_results, start=1):
                        error = abs(result - self.task2_target_radius)
                        print(f"Trial {i}: achieved={result}, error={error}")
                    avg_error = sum(abs(r - self.task2_target_radius) for r in self.task2_results) / len(self.task2_results)
                    print("Average absolute error:", avg_error)
                    print("---------------------------------------------------")
                    sys.exit(0)
                

        #VISUALIZATION OF EXPERIMENT 1

        if g.task1:
            #visualization of ball
            current_time = pygame.time.get_ticks() / 1000 #get current time at each frame
            pygame.draw.circle(g.screenReference, g.cIce, (int(self.x_ball), int(self.y_ball)), new_ball_radius, 0)
            pygame.draw.circle(g.screenReference, g.cIce, (int(self.x_ball), int(self.y_ball)),
                               int(self.R + self.offset / 2), 2)
            self.last_rec_radius = new_ball_radius

            if (current_time-self.start_time_exp1) > 10.00:
                #error analysis
                absolute_error = abs(g.reference_radius - self.last_rec_radius)
                percentage_error = abs(g.reference_radius - self.last_rec_radius)/g.reference_radius * 100


                # self.task1_finished = False
                print("Task 1 Trial Finished!")
                print("RESULTS")
                print("---------------------------------------------------")
                print("Using Haply: ", self.device_connected)
                print("Target Radius:", g.reference_radius, "pixels")
                print("Achieved Radius:", self.last_rec_radius, "pixels" )
                print("Absolute Error:", absolute_error)
                print("Percentage Error:", percentage_error, "%")
                print("---------------------------------------------------")
                sys.exit(0)

        # VISUALIZATION / LOGIC OF EXPERIMENT 2
        if g.task2 == True:
            if self.task2_finished and self.task2_finish_time is not None:
                if pygame.time.get_ticks() - self.task2_finish_time >= 2000:
                    print("Task 2 Finished!")
                    print("---------------------------------------------------")
                    print("Using Haply:", self.device_connected)
                    print("Target size:", self.task2_target_radius)
                    for i, result in enumerate(self.task2_results, start=1):
                        error = abs(result - self.task2_target_radius)
                        print(f"Trial {i}: achieved={result}, error={error}")
                    avg_error = sum(abs(r - self.task2_target_radius) for r in self.task2_results) / len(self.task2_results)
                    print("Average absolute error:", avg_error)
                    print("---------------------------------------------------")
                    sys.exit(0)

        g.task2_stage = self.task2_stage
        g.task2_current_trial = self.task2_current_trial
        g.task2_total_trials = self.task2_total_trials
        g.task2_target_radius = self.task2_target_radius
        g.task2_first_snowball_size = self.task2_first_snowball_size
        g.task2_results = self.task2_results
        g.task2_initial_ball_size_at_startup = self.task2_initial_ball_size_at_startup

        #implement melting
        if (self.R > self.R_min):
            self.R = self.R *self.radius_melting_gain

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