# -*- coding: utf-8 -*-

import pygame
import numpy as np
# import math
# import matplotlib.pyplot as plt
# from HaplyHAPI import Board, Device, Mechanisms, Pantograph
import sys, serial, glob
# from serial.tools import list_ports
import time
import pygame.gfxdraw

class Graphics:
    def __init__(self, device_connected, window_size=(600, 400)):
        self.device_connected = device_connected

        # initialize pygame window
        self.window_size = window_size  # default (600,400)
        pygame.init()
        self.window = pygame.display.set_mode((window_size[0] * 2, window_size[1] *2))  ##twice 600x400 for haptic and VR
        pygame.display.set_caption('Virtual Haptic Device')

        #Menu screen
        self.screenMenu = pygame.Surface((self.window_size[0]*2, self.window_size[1]*2))

        self.screenHaptics = pygame.Surface(self.window_size)
        self.screenVR = pygame.Surface(self.window_size)
        self.screenField= pygame.Surface(self.window_size)
        self.screenReference = pygame.Surface(self.window_size)

        # self.screenTask1Menu = pygame.Surface(self.window_size)

        ##add nice icon from https://www.flaticon.com/authors/vectors-market
        self.icon = pygame.image.load('robot.png')
        pygame.display.set_icon(self.icon)

        ##add text on top to debugToggle the timing and forces
        self.font = pygame.font.Font('freesansbold.ttf', 18)
        self.instructions_font = pygame.font.Font('freesansbold.ttf', 12)
        self.menutitle_font = pygame.font.Font('Bangers-Regular.ttf', 40)
        self.menu_subtitle_font = pygame.font.Font('Bangers-Regular.ttf', 25)

        pygame.mouse.set_visible(True)  ##Hide cursor by default. 'm' toggles it

        ##set up the on-screen debugToggle
        self.text = self.font.render('Virtual Haptic Device', True, (0, 0, 0), (255, 255, 255))
        self.textRect = self.text.get_rect()
        self.textRect.topleft = (10, 10)

        # xc,yc = screenVR.get_rect().center ##center of the screen

        ##initialize "real-time" clock
        self.clock = pygame.time.Clock()
        self.FPS = 100 # in Hertz

        ##define some colors
        self.cWhite = (255, 255, 255)
        self.cDarkblue = (36, 90, 190)
        self.cLightblue = (0, 176, 240)
        self.cRed = (255, 0, 0)
        self.cOrange = (255, 128, 0)#(255, 100, 0)
        self.cDarkOrange = (179, 71, 0)#(255, 100, 0)
        self.cYellow = (255, 255, 0)
        self.cIce = (204, 255, 255)
        self.cGreen1 = (0, 153, 0) #fully clean green
        self.cGreen2 = (102, 255, 102)  # semi clean green
        self.cGreen3 = (204, 255, 204)  # light green
        self.cBlack = (0,0,0)
        self.cGrey = (213, 218, 219)


        self.hhandle = pygame.image.load('handle.png')  #

        #use nice image for glove from https://www.flaticon.com/free-icons/christmas
        self.glove = pygame.image.load('christmas-gloves.png')


        self.haptic_width = 48
        self.haptic_height = 48
        self.haptic = pygame.Rect(*self.screenHaptics.get_rect().center, 0, 0).inflate(self.haptic_width, self.haptic_height)
        self.effort_cursor = pygame.Rect(*self.haptic.center, 0, 0).inflate(self.haptic_width, self.haptic_height)
        self.colorHaptic = self.cOrange  ##color of the wall

        ####Pseudo-haptics dynamic parameters, k/b needs to be <1
        self.sim_k = 0.5  # 0.1#0.5       ##Stiffness between cursor and haptic display
        self.sim_b = 0.8  # 1.5#0.8       ##Viscous of the pseudohaptic display

        self.window_scale = 3000  # 2500 #pixels per meter
        self.device_origin = (int(self.window_size[0] / 2.0 + 0.038 / 2.0 * self.window_scale), 0)

        self.show_linkages = True
        self.show_debug = True

        # Task flags, they determine what shows up on the bottom left screen
        self.menu = True #Showing the menu to choose tasks
        self.task1 = False #Making snowballs of a specific size
        self.task2 = False #Estimating snowball size 
        self.task3 = False #Navigating flowers in the environment

        self.task1_intro = False
        self.task2_intro = False
        self.task3_intro = False
        
        self.flower_positions = []
        self.current_collisions = 0

        #Task 1 variables
        self.reference_radius = 0

        # Task2 Variables
        self.task2_stage = 0
        self.task2_current_trial = 0
        self.task2_total_trials = 5
        self.task2_target_radius = 50
        self.task2_first_snowball_size = None
        self.task2_results = []

        self.task2_results = []
        self.task2_initial_ball_size_at_startup = None


        #menu variables
        self.exp1buttoncolour = self.cOrange
        self.exp2buttoncolour = self.cOrange
        self.exp3buttoncolour = self.cOrange

    def draw_leaf(self, x, y):
        pygame.draw.polygon(self.screenMenu, self.cGreen2,[(x, y), (x - 20, y - 40), (x + 20, y - 30)])
        pygame.draw.polygon(self.screenMenu, self.cGreen1,  [(x, y), (x - 30, y - 20), (x - 5, y - 35)])
        pygame.draw.polygon(self.screenMenu, self.cGreen3,  [(x, y), (x - 10, y - 50), (x + 10, y - 30)])



    def convert_pos(self, *positions):
        # invert x because of screen axes
        # 0---> +X
        # |
        # |
        # v +Y
        converted_positions = []
        for physics_pos in positions:
            x = self.device_origin[0] - physics_pos[0] * self.window_scale
            y = self.device_origin[1] + physics_pos[1] * self.window_scale
            converted_positions.append([x, y])
        if len(converted_positions) <= 0:
            return None
        elif len(converted_positions) == 1:
            return converted_positions[0]
        else:
            return converted_positions
        return [x, y]

    def inv_convert_pos(self, *positions):
        # convert screen positions back into physical positions
        converted_positions = []
        for screen_pos in positions:
            x = (self.device_origin[0] - screen_pos[0]) / self.window_scale
            y = (screen_pos[1] - self.device_origin[1]) / self.window_scale
            converted_positions.append([x, y])
        if len(converted_positions) <= 0:
            return None
        elif len(converted_positions) == 1:
            return converted_positions[0]
        else:
            return converted_positions
        return [x, y]

    def get_events(self):
        #########Process events  (Mouse, Keyboard etc...)#########
        events = pygame.event.get()
        keyups = []
        mouse_clicks = []

        for event in events:
            if event.type == pygame.QUIT:  # close window button was pressed
                sys.exit(0)  # raises a system exit exception so any Finally will actually execute
            elif event.type == pygame.KEYUP:
                keyups.append(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_clicks.append(event.pos)

        mouse_pos = pygame.mouse.get_pos()
        return keyups, mouse_pos, mouse_clicks

    def sim_forces(self, pE, f, pM, mouse_k=None, mouse_b=None):
        # simulated device calculations
        if mouse_k is not None:
            self.sim_k = mouse_k
        if mouse_b is not None:
            self.sim_b = mouse_b
        if not self.device_connected:
            pP = self.haptic.center
            # pM is where the mouse is
            # pE is where the position is pulled towards with the spring and damping factors
            # pP is where the actual haptic position ends up as
            diff = np.array((pM[0] - pE[0], pM[1] - pE[1]))
            # diff = np.array(( pM[0]-pP[0],pM[1]-pP[1]) )

            scale = self.window_scale / 1e3
            scaled_vel_from_force = np.array(f) * scale / self.sim_b
            vel_from_mouse_spring = (self.sim_k / self.sim_b) * diff
            dpE = vel_from_mouse_spring - scaled_vel_from_force
            # dpE = -dpE
            # if diff[0]!=0:
            #    if (diff[0]+dpE[0])/diff[0]<0:
            #        #adding dpE has changed the sign (meaning the distance that will be moved is greater than the original displacement
            #        #prevent the instantaneous velocity from exceeding the original displacement (doesn't make physical sense)
            #        #basically if the force given is so high that in a single "tick" it would cause the endpoint to move back past it's original position...
            #        #whatever thing is exerting the force should basically be considered a rigid object
            #        dpE[0] = -diff[0]
            # if diff[1]!=1:
            #    if (diff[1]+dpE[1])/diff[1]<0:
            #        dpE[1] = -diff[1]
            if abs(dpE[0]) < 1:
                dpE[0] = 0
            if abs(dpE[1]) < 1:
                dpE[1] = 0
            pE = np.round(pE + dpE)  # update new positon of the end effector

            # Change color based on effort
            cg = 255 - np.clip(np.linalg.norm(self.sim_k * diff / self.window_scale) * 255 * 20, 0, 255)
            cb = 255 - np.clip(np.linalg.norm(self.sim_k * diff / self.window_scale) * 255 * 20, 0, 255)
            self.effort_color = (255, cg, cb)
        return pE

    def erase_screen(self):
        self.screenHaptics.fill(self.cWhite)  # erase the haptics surface
        self.screenVR.fill(self.cWhite)  # erase the VR surface
        self.screenField.fill(self.cWhite)  # Added
        self.screenReference.fill(self.cWhite)
        self.screenMenu.fill(self.cWhite)
        self.debug_text = ""

        # if self.task3 == True:
        #     self.screenReference.fill(self.cGreen1)

    def render(self, pA0, pB0, pA, pB, pE, f, pM):
        ###################Render the Haptic Surface###################
        # set new position of items indicating the endpoint location
        self.haptic.center = pE  # the hhandle image and effort square will also use this position for drawing
        self.effort_cursor.center = self.haptic.center

        if self.device_connected:
            self.effort_color = (255, 255, 255)

        # pygame.draw.rect(self.screenHaptics, self.effort_color, self.haptic,border_radius=4)
        pygame.draw.rect(self.screenHaptics, self.effort_color, self.effort_cursor, border_radius=8)

        #home button to get back to menu
        # Add nice image from  https://www.flaticon.com/free-icons/home-button
        self.home = pygame.image.load('home.png')
        self.home = pygame.transform.smoothscale(self.home, (30, 30))
        self.home_rect = self.home.get_rect(topleft=(10, 50))

        self.screenHaptics.blit(self.home, self.home_rect.topleft)


        ######### Robot visualization ###################
        if self.show_linkages:
            pantographColor = (150, 150, 150)
            pygame.draw.lines(self.screenHaptics, pantographColor, False, [pA0, pA], 15)
            pygame.draw.lines(self.screenHaptics, pantographColor, False, [pB0, pB], 15)
            pygame.draw.lines(self.screenHaptics, pantographColor, False, [pA, pE], 15)
            pygame.draw.lines(self.screenHaptics, pantographColor, False, [pB, pE], 15)

            for p in (pA0, pB0, pA, pB, pE):
                pygame.draw.circle(self.screenHaptics, (0, 0, 0), p, 15)
                pygame.draw.circle(self.screenHaptics, (200, 200, 200), p, 6)

        ### Hand visualisation
        self.screenHaptics.blit(self.hhandle, self.effort_cursor)
        self.screenVR.blit(self.glove, self.haptic)

        # pygame.draw.line(self.screenHaptics, (0, 0, 0), (self.haptic.center),(self.haptic.center+2*k*(xm-xh)))

        if self.task1_intro:
            lines = [
                "Task 1: Making a snowball of specific size",
                "",
                "Screen layout:",
                "Top left: movement of the haptic device (bird's-eye view).",
                "Top right: the simulated snowball. It grows as you roll it,",
                "and it can also melt. The ball is red when you are not",
                "exerting force on it, and green when you are.",
                "Bottom left: the movement of the snowball in the open world.",
                "As the ball moves, it leaves a green trail, showing grass",
                "under the snow.",
                "Bottom right: the experiment display.",
                "",
                "Task:",
                "After pressing ENTER, you will see a snowball and ",
                "an outline showing the desired reference size. Your goal is to make the",
                "snowball match the reference size as closely as possible.",
                "You will have 10 seconds, after which the simulation ends. You can now play around ",
                "with the controls to get a feeling for how it operates.",
                "When you are ready, press ENTER to start ."
            ]
            for i, line in enumerate(lines):
                text = self.instructions_font.render(line, True, self.cBlack)
                self.screenReference.blit(text, (10, 10 + i * 20))


        if self.task2_intro:
            lines = [
                "Task 2: Reproducing Snowball Size",
                "Screen layout:",
                "Top left: movement of the haptic device (bird's-eye view).",
                "Top right: the simulated snowball. It grows as you roll it,",
                "and it can also melt. The ball is red when you are not",
                "exerting force on it, and green when you are.",
                "Bottom left: the movement of the snowball in the open world.",
                "As the ball moves, it leaves a green trail, showing grass",
                "under the snow.",
                "Bottom right: the experiment display.",
                "",
                "Task:",
                "Focus on the top right screen for this experiment, on the red snowball size.",
                "After pressing ENTER, you will first make a snowball of any size to get",
                "a sense of scale. After accepting it with X, its size will be shown. You will then",
                f"be asked to make 10 snowballs of size {self.task2_target_radius}.",
                "After each trial, you will see the size of the snowball you made for reference.",
                "After each trial, the ball returns to its initial size. You can now play around",
                "with the controls to get a feeling for how it operates. When you are ready press ENTER to start.",
            ]
            for i, line in enumerate(lines):
                text = self.instructions_font.render(line, True, self.cBlack)
                self.screenReference.blit(text, (10, 10 + i * 20))


        if self.task3_intro:
            lines = [
                "Task 3: Navigating through the maze",

                "Screen layout:",
                "Top left: movement of the haptic device (bird's-eye view).",
                "Top right: the simulated snowball. It grows as you roll it,",
                "and it can also melt. The ball is red when you are not",
                "exerting force on it, and green when you are.",
                "Bottom left: the movement of the snowball in the open world.",
                "As the ball moves, it leaves a green trail, showing grass",
                "under the snow.",
                "Bottom right: the experiment display.",
                "",
                "Task:",
                "After pressing ENTER, you will see a maze made out of flowers.",
                "Your goal is to complete the maze while hitting as few",
                "walls of flowers as possible. After each hit, the snowball is moved back to",
                " the middle of the corridor at the place where the flower was hit.",
                "You can now play around with the controls to get a feeling for how it operates.",
                "When you are ready Press ENTER when you are ready.",
                "Important: Try pushing the ball slowly!",
            ]
            for i, line in enumerate(lines):
                text = self.instructions_font.render(line, True, self.cBlack)
                self.screenReference.blit(text, (10, 10 + i * 20))
        ########################Task 3 Visuals #################################################33
        if self.task3 == True:

            text_surface = self.font.render(f"Collisions: {self.current_collisions}", True, (255, 0, 0))
            self.screenReference.blit(text_surface, (220, 280))  # top-left corner

            #Add nice image from  https://www.flaticon.com/free-icons/flower
            self.flower= pygame.image.load('flower.png')
            self.flower = pygame.transform.smoothscale(self.flower, (20, 20))

            #draw endgoal
            pygame.draw.rect(self.screenReference, (0,255,0), (220,300, 60,60))

            def add_flower(x, y):
                self.screenReference.blit(self.flower, (x, y))
                self.flower_positions.append((x + 10, y + 10))  # store CENTER (20x20 → +10)

            self.flower_positions = []

            #borders
            for i in range(30):
                add_flower(i * 20, 0)
                add_flower(i * 20, 380)

            for i in range(20):
                add_flower(0, i * 20)
                add_flower(580, i * 20)

            for i in range(4):
                #tunnel 1 ()
                add_flower((20*i)+200, 0)



            for i in range(7):
                #tunnel 3 (right wall)
                add_flower(80, (20*i)+180)

            for i in range(8):
                #tunnel 3 (right wall)
                add_flower(180, 400-(20*i))
                #tunnel 5 (bottom wall)
                add_flower(200+(20*i), 260)
                add_flower(360+(20*i), 80)

            # tunnel 1 + others
            for i in range(9):
                add_flower(260, (20*i))
                add_flower(500, 100+(20*i))

            for i in range(10):
                #tunnel 1 (top and bottom)
                add_flower((20*i), 0)
                add_flower((20*i), 80)

                add_flower((20*i)+80, 160)
                add_flower(340, 260-(20*i))
                add_flower(420, 180+(20*i))

            """
            for i in range(30):
                self.screenReference.blit(self.flower, [i * 20, 0])
                self.screenReference.blit(self.flower, [i * 20, 380])
            for i in range(20):
                self.screenReference.blit(self.flower, [0, i * 20])
                self.screenReference.blit(self.flower, [580, i * 20])
           
            
           
            for i in range(4):
                #tunnel 1 ()
                self.screenReference.blit(self.flower, [((20*i)+200), 0])
            
            
            #for i in range(6):        
                
                
            
            for i in range(7):
                #tunnel 3 (right wall)
                self.screenReference.blit(self.flower, [(80), ((20*i)+180)])
                
                
                
            
            for i in range (8):
                #tunnel 3 (right wall)
                self.screenReference.blit(self.flower, [(180), (400- (20*i))])
                
                
                
                #tunnel 5 (bottom wall)
                self.screenReference.blit(self.flower, [(200+(20*i)), (260)])
                
                
                #tunnel 7 (bottom wall)
                self.screenReference.blit(self.flower, [360+(20*i), 80])
                
            
            for i in range(9):
                #tunnel 1 (right wall)
                self.screenReference.blit(self.flower, [260, (20*i)])
                
                
                #tunnel 8 (left wall)
                self.screenReference.blit(self.flower, [500, 100+(20*i)])
                
                
                
            for i in range(10):
                #tunnel 1 (top and bottom)
                self.screenReference.blit(self.flower, [(20*i), 0])
                self.screenReference.blit(self.flower, [(20*i), 80])
                
                #tunnel 2 (bottom wall)
                self.screenReference.blit(self.flower, [((20*i)+80), (160)])
                pygame.draw.circle(self.screenReference, (0, 0, 255), [(20*i)+80+10, 160+10], 10)
                
                
                #tunnel 6 (right wall)
                self.screenReference.blit(self.flower, [340, 260-(20*i)])
                pygame.draw.circle(self.screenReference, (0, 0, 255), [340+10, 260-(20*i)+10], 10)
                
                #tunnel 9 (left wall)
                self.screenReference.blit(self.flower, [420, 180+(20*i)])
                
            #for i in range(11):
                """

        #Task 1 visuals
        if self.task1:
            #instructions
            #instructions1 = self.instructions_font.render(f"Can you make the snowball reach the reference radius without overshooting? ", True, self.cBlack)
            #instructions2 = self.instructions_font.render("Careful! Your snowball is also melting over time.", True, self.cBlack)            
            instructions1 = self.instructions_font.render(f" ", True, self.cBlack)
            instructions2 = self.instructions_font.render(" ", True, self.cBlack)            
            self.screenReference.blit(instructions1, (10, 10))
            self.screenReference.blit(instructions2, (10, 40))

            #reference circle
            self.reference_radius = 100
            pygame.draw.circle(self.screenReference, self.cGrey, (300, 200), self.reference_radius, 2)

        #MENU VISUALIZATION
        if self.menu:
            menu_title1= self.menutitle_font.render("TURBO SNOWMAN-MAKING", True, self.cBlack)
            menu_title2 = self.menutitle_font.render("SIMULATOR X-TREME 3000", True, self.cBlack)
            menu_subtitle = self.menu_subtitle_font.render("RO47013 - CHR-Ice", True, self.cBlack)

            #ice slope
            pygame.gfxdraw.filled_trigon(self.screenMenu,0, 800,1200, 800,0, 500, self.cIce)
            #snowball balls
            pygame.draw.circle(self.screenMenu, self.cIce, (200, 490), 80, 0)
            pygame.draw.circle(self.screenMenu, self.cIce, (200, 360), 60, 0)
            pygame.draw.circle(self.screenMenu, self.cIce, (200, 270), 40, 0)

            #buttons - bottom snowball
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 450), 5, 0)
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 490), 5, 0)
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 530), 5, 0)
            #buttons - middle snowball
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 320), 5, 0)
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 360), 5, 0)
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 400), 5, 0)

            #eyes - top snowball
            pygame.draw.circle(self.screenMenu, self.cBlack, (190, 260), 4, 0)
            pygame.draw.circle(self.screenMenu, self.cBlack, (210, 260), 4, 0)
            #smile
            pygame.draw.arc(self.screenMenu,self.cBlack,(185, 270, 30, 20),np.pi,  0,2 )
            #carrot nse
            pygame.gfxdraw.filled_trigon(self.screenMenu, 200, 260, 200, 275, 250, 270, self.cOrange)

            #hat!
            self.hat = pygame.image.load('hat.png')
            self.hat = pygame.transform.smoothscale(self.hat, (85, 85))
            self.screenMenu.blit(self.hat, (145, 160))
            #scarf!
            self.scarf = pygame.image.load('scarf.png')
            self.scarf = pygame.transform.smoothscale(self.scarf, (55, 55))
            self.screenMenu.blit(self.scarf, (175, 300))

            self.screenMenu.blit(menu_title1, (500, 100))
            self.screenMenu.blit(menu_title2, (500, 150))
            self.screenMenu.blit(menu_subtitle, (600, 200))

            #Experiment Buttons
            experiment1_text = self.menu_subtitle_font.render("Experiment 1", True, self.cBlack)
            experiment2_text = self.menu_subtitle_font.render("Experiment 2", True, self.cBlack)
            experiment3_text = self.menu_subtitle_font.render("Experiment 3", True, self.cBlack)

            pygame.gfxdraw.filled_trigon(self.screenMenu, 580, 315, 580, 410, 850, 362, self.exp1buttoncolour) #experimetn 1
            pygame.gfxdraw.filled_trigon(self.screenMenu, 580, 415, 580, 510, 850, 462, self.exp2buttoncolour) #experiment 2
            pygame.gfxdraw.filled_trigon(self.screenMenu, 580, 515, 580, 610, 850, 562, self.exp3buttoncolour) #experiment 3

            #Leaves for the carrots
            self.draw_leaf(580, 363)
            self.draw_leaf(580, 463)
            self.draw_leaf(580, 563)

            self.screenMenu.blit(experiment1_text, (600, 350))
            self.screenMenu.blit(experiment2_text, (600, 450))
            self.screenMenu.blit(experiment3_text, (600, 550))

            #ice slope
            pygame.gfxdraw.filled_trigon(self.screenMenu,0, 800,1200, 800,0, 500, self.cIce)
            #snowball balls
            pygame.draw.circle(self.screenMenu, self.cIce, (200, 490), 80, 0)
            pygame.draw.circle(self.screenMenu, self.cIce, (200, 360), 60, 0)
            pygame.draw.circle(self.screenMenu, self.cIce, (200, 270), 40, 0)

            #buttons - bottom snowball
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 450), 5, 0)
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 490), 5, 0)
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 530), 5, 0)
            #buttons - middle snowball
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 320), 5, 0)
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 360), 5, 0)
            pygame.draw.circle(self.screenMenu, self.cBlack, (200, 400), 5, 0)

            #eyes - top snowball
            pygame.draw.circle(self.screenMenu, self.cBlack, (190, 260), 4, 0)
            pygame.draw.circle(self.screenMenu, self.cBlack, (210, 260), 4, 0)
            #smile
            pygame.draw.arc(self.screenMenu,self.cBlack,(185, 270, 30, 20),np.pi,  0,2 )
            #carrot nse
            pygame.gfxdraw.filled_trigon(self.screenMenu, 200, 260, 200, 275, 250, 270, self.cOrange)

            #hat!
            self.hat = pygame.image.load('hat.png')
            self.hat = pygame.transform.smoothscale(self.hat, (85, 85))
            self.screenMenu.blit(self.hat, (145, 160))
            #scarf!
            self.scarf = pygame.image.load('scarf.png')
            self.scarf = pygame.transform.smoothscale(self.scarf, (55, 55))
            self.screenMenu.blit(self.scarf, (175, 300))

            self.screenMenu.blit(menu_title1, (500, 100))
            self.screenMenu.blit(menu_title2, (500, 150))
            self.screenMenu.blit(menu_subtitle, (600, 200))

            #Experiment Buttons
            experiment1_text = self.menu_subtitle_font.render("Experiment 1", True, self.cBlack)
            experiment2_text = self.menu_subtitle_font.render("Experiment 2", True, self.cBlack)
            experiment3_text = self.menu_subtitle_font.render("Experiment 3", True, self.cBlack)

            pygame.gfxdraw.filled_trigon(self.screenMenu, 580, 315, 580, 410, 850, 362, self.exp1buttoncolour) #experimetn 1
            pygame.gfxdraw.filled_trigon(self.screenMenu, 580, 415, 580, 510, 850, 462, self.exp2buttoncolour) #experiment 2
            pygame.gfxdraw.filled_trigon(self.screenMenu, 580, 515, 580, 610, 850, 562, self.exp3buttoncolour) #experiment 3

            #Leaves for the carrots
            self.draw_leaf(580, 363)
            self.draw_leaf(580, 463)
            self.draw_leaf(580, 563)

            self.screenMenu.blit(experiment1_text, (600, 350))
            self.screenMenu.blit(experiment2_text, (600, 450))
            self.screenMenu.blit(experiment3_text, (600, 550))

            ###################Render the VR surface###################
        # pygame.draw.rect(self.screenVR, self.colorHaptic, self.haptic, border_radius=8)

        if self.task2 == True:
            if self.task2_stage == 0:
                instructions1 = self.instructions_font.render(
                    "This experiment tests your ability to estimate snowball size.",
                    True, self.cBlack
                )
                instructions2 = self.instructions_font.render(
                    "First, make a snowball of any size.",
                    True, self.cBlack
                )
                instructions3 = self.instructions_font.render(
                    "Press 'X' when you are happy with the size of your snowball.",
                    True, self.cBlack
                )

                self.screenReference.blit(instructions1, (10, 10))
                self.screenReference.blit(instructions2, (10, 40))
                self.screenReference.blit(instructions3, (10, 70))

            elif self.task2_stage == 1:
                instructions1 = self.instructions_font.render(
                    f"Make a snowball of size {self.task2_target_radius}. Press 'X' when ready.",
                    True, self.cBlack
                )
                instructions2 = self.instructions_font.render(
                    f"Trial {min(self.task2_current_trial + 1, self.task2_total_trials)} / {self.task2_total_trials}",
                    True, self.cBlack
                )

                self.screenReference.blit(instructions1, (10, 10))
                self.screenReference.blit(instructions2, (10, 40))

                y0 = 90
                # Show reference (first free try)
                if self.task2_first_snowball_size is not None:
                    ref_text = self.instructions_font.render(
                        f"Your trial snowball size: {self.task2_first_snowball_size}",
                        True,
                        self.cBlack
                    )
                    self.screenReference.blit(ref_text, (10, y0))
                    y0 += 30

                # Show trials
                for i, result in enumerate(self.task2_results, start=1):
                    error = abs(result - self.task2_target_radius)
                    result_text = self.instructions_font.render(
                        f"Trial {i}: size = {result}, error = {error}",
                        True,
                        self.cBlack
                    )
                    self.screenReference.blit(result_text, (10, y0))
                    y0 += 30

        if not self.device_connected:
            pygame.draw.lines(self.screenHaptics, (0, 0, 0), False, [self.effort_cursor.center, pM], 2)
        ##Fuse it back together
        if self.menu:
            self.window.blit(self.screenMenu, (0, 0))
        else:
            self.window.blit(self.screenHaptics, (0, 0))
            self.window.blit(self.screenVR, (600, 0))
            self.window.blit(self.screenField, (0, 400))
            self.window.blit(self.screenReference, (600, 400))

        ##Print status in  overlay
        if self.show_debug:
            self.debug_text += "FPS = " + str(round(self.clock.get_fps())) + " "
            self.debug_text += "fe: " + str(np.round(f[0], 1)) + "," + str(np.round(f[1], 1)) + "] "
            self.debug_text += "xh: [" + str(np.round(pE[0], 1)) + "," + str(np.round(pE[1], 1)) + "]"
            self.text = self.font.render(self.debug_text, True, (0, 0, 0), (255, 255, 255))
            self.window.blit(self.text, self.textRect)

        pygame.display.flip()
        ##Slow down the loop to match FPS
        self.clock.tick(self.FPS)

    def close(self):
        pygame.display.quit()
        pygame.quit()

