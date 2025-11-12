import pygame as pg
import math
import random

SCREEN_WIDTH = 1920 / 2
SCREEN_HEIGHT = 1080 / 2
FPS = 60
MAX_SPEED = 600
PLAYER_SIZE = 20

ACCELERATION = 1200
DRIFT_THRESHOLD = 100

# Physique plus glissante
STEER_SPEED_NORMAL = 3.5
STEER_SPEED_DRIF = 4.5
NORMAL_LONG_FRIC = 2.5
NORMAL_LAT_FRIC = 4.0
DRIFT_LONG_FRIC = 4.0
DRIFT_LAT_FRIC = 0.05    # TRÈS GLISSANT
AIR_DRAG_COEFF = 1.2
ROLLING_RESIST = 120

def get_inputs():
    keys = pg.key.get_pressed()
    forward = keys[pg.K_w] or keys[pg.K_UP]
    backward = keys[pg.K_s] or keys[pg.K_DOWN]
    steer_left = keys[pg.K_a] or keys[pg.K_LEFT]
    steer_right = keys[pg.K_d] or keys[pg.K_RIGHT]
    space_pressed = keys[pg.K_SPACE]
    
    steer_input = (1 if steer_right else 0) - (1 if steer_left else 0)
    throttle = (1.0 if forward else 0.0) - (0.8 if backward else 0.0)
    
    return steer_input, throttle, space_pressed

def update_steering(player_angle, steer_input, speed, is_drifting, dt):
    steer_speed = STEER_SPEED_DRIF if is_drifting else STEER_SPEED_NORMAL
    steer_mult = max(0.3, 1.0 - speed / (MAX_SPEED * 1.2))
    player_angle += steer_input * steer_speed * steer_mult * dt
    return player_angle

def update_velocity(velocity, player_angle, throttle, is_drifting, speed, dt):
    facing = pg.Vector2(math.cos(player_angle), math.sin(player_angle))
    
    forward_vel = velocity.dot(facing)
    side_vel = velocity - facing * forward_vel
    slip_ratio = abs(side_vel.length() / max(speed, 1.0))
    traction = math.sqrt(max(0.0, 1.0 - slip_ratio ** 1.5))
    velocity += facing * ACCELERATION * throttle * traction * dt
    
    long_fric_factor = DRIFT_LONG_FRIC if is_drifting else NORMAL_LONG_FRIC
    lat_fric_factor = DRIFT_LAT_FRIC if is_drifting else NORMAL_LAT_FRIC
    long_friction = -facing * forward_vel * long_fric_factor * dt
    side_friction = -side_vel * lat_fric_factor * dt
    velocity += long_friction + side_friction
    
    if speed > 0:
        drag_dir = velocity.normalize()
        air_drag = drag_dir * (speed * AIR_DRAG_COEFF * dt)
        rolling_drag = drag_dir * ROLLING_RESIST * dt
        velocity -= air_drag + rolling_drag
    
    if speed > MAX_SPEED:
        velocity.scale_to_length(MAX_SPEED)
    
    return velocity

def update_position(player_pos, velocity, dt):
    player_pos += velocity * dt
    half_size = PLAYER_SIZE / 2
    player_pos.x = max(half_size, min(player_pos.x, SCREEN_WIDTH - half_size))
    player_pos.y = max(half_size, min(player_pos.y, SCREEN_HEIGHT - half_size))
    return player_pos

def create_car_surface():
    car_length = PLAYER_SIZE * 1.6  # 32
    car_width = PLAYER_SIZE         # 20
    unrot_surf = pg.Surface((int(car_length), int(car_width)), pg.SRCALPHA)
    pg.draw.rect(unrot_surf, (200, 50, 50), (0, 0, car_length, car_width))
    # Phares avant (côté droit)
    pg.draw.rect(unrot_surf, (255, 255, 200), (car_length - 8, 2, 6, 7))
    pg.draw.rect(unrot_surf, (255, 255, 200), (car_length - 8, car_width - 9, 6, 7))
    return unrot_surf

def draw_car(screen, unrot_surf, player_pos, player_angle):
    unrot_rect = unrot_surf.get_rect(center=player_pos)
    angle_deg = -math.degrees(player_angle)
    rot_surf = pg.transform.rotate(unrot_surf, angle_deg)
    rot_rect = rot_surf.get_rect(center=unrot_rect.center)
    screen.blit(rot_surf, rot_rect.topleft)

def emit_particles(particles, player_pos, player_angle, is_drifting, side_vel, velocity, dt):
    """Émet des particules à l'arrière"""
    if is_drifting and side_vel.length() > 20:
        # Offset arrière dans le repère de la voiture (avant rotation)
        rear_offset_local = pg.Vector2(-PLAYER_SIZE * 1.6 / 2, 0)  # Arrière
        rear_offset = rear_offset_local.rotate(math.degrees(player_angle))  # Roté
        
        for _ in range(5):
            # Petit offset aléatoire autour de l'arrière
            smoke_off = pg.Vector2(random.uniform(-6, -16), random.uniform(-8, 8))
            smoke_off = smoke_off.rotate(math.degrees(player_angle))
            
            # Vélocité de la particule : un peu de vitesse voiture + poussée arrière
            particle_vel = velocity * 0.15 + rear_offset.normalize() * -8
            
            particles.append({
                'pos': player_pos + rear_offset + smoke_off,
                'life': random.uniform(0.7, 1.3),
                'size': random.uniform(5, 12),
                'velocity': particle_vel
            })

def update_and_draw_particles(screen, particles, dt):
    for p in particles[:]:
        p['life'] -= dt
        if p['life'] <= 0:
            particles.remove(p)
            continue
        p['pos'] += p['velocity'] * dt
        alpha = int(200 * (p['life'] / 1.3))
        ssize = p['size']
        smoke_surf = pg.Surface((ssize*2, ssize*2), pg.SRCALPHA)
        pg.draw.circle(smoke_surf, (100, 90, 70, alpha), (ssize, ssize), ssize)
        screen.blit(smoke_surf, (p['pos'].x - ssize, p['pos'].y - ssize))

def draw_hud(screen, font, speed, side_vel, is_drifting, traction, player_angle):
    info = [
        f"Vitesse: {speed:.0f}",
        f"Glisse lat: {side_vel.length():.0f}",
        f"DRIFT: {'ON' if is_drifting else 'OFF'}",
        f"Traction: {traction:.2f}",
        f"Angle: {math.degrees(player_angle) % 360:.0f}°"
    ]
    y = 10
    for line in info:
        surf = font.render(line, True, (255, 255, 255))
        screen.blit(surf, (10, y))
        y += 25
    
    instr = font.render("W=accél | S=frein | A/D=braque | SPACE=DRIFT", True, (180, 220, 180))
    screen.blit(instr, (10, SCREEN_HEIGHT - 35))

def main():
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pg.time.Clock()
    running = True
    font = pg.font.Font(None, 24)
    particles = []
    
    player_pos = pg.Vector2(screen.get_width() / 2, screen.get_height() / 2)
    velocity = pg.Vector2(0, 0)
    player_angle = 0.0
    
    car_surf = create_car_surface()

    while running:
        dt = clock.tick(FPS) / 1000
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

        screen.fill("black")
        
        steer_input, throttle, space_pressed = get_inputs()
        speed = velocity.length()
        is_drifting = space_pressed and speed > DRIFT_THRESHOLD
        
        player_angle = update_steering(player_angle, steer_input, speed, is_drifting, dt)
        velocity = update_velocity(velocity, player_angle, throttle, is_drifting, speed, dt)
        player_pos = update_position(player_pos, velocity, dt)
        
        # Calcul side_vel pour particules
        facing = pg.Vector2(math.cos(player_angle), math.sin(player_angle))
        forward_vel = velocity.dot(facing)
        side_vel = velocity - facing * forward_vel
        
        # Émission particules (velocity passé !)
        emit_particles(particles, player_pos, player_angle, is_drifting, side_vel, velocity, dt)
        
        draw_car(screen, car_surf, player_pos, player_angle)
        update_and_draw_particles(screen, particles, dt)
        
        slip_ratio = abs(side_vel.length() / max(speed, 1.0))
        traction = math.sqrt(max(0.0, 1.0 - slip_ratio ** 1.5))
        draw_hud(screen, font, speed, side_vel, is_drifting, traction, player_angle)
        
        pg.display.flip()
    pg.quit()

if __name__ == "__main__":
    main()