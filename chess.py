"""
Chess AI with Alpha-Beta Pruning
=================================
Controls:
  - Click a piece to select it (highlighted in gold)
  - Click a valid square to move
  - Press 'R' to reset the game
  - Press 'U' to undo your last move
  - Press 'A' to toggle AI on/off
  - Press 'ESC' to quit

Requirements:
  pip install pygame
"""

import pygame
import sys
import copy
import time

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
WIDTH, HEIGHT = 720, 720
BOARD_SIZE = 8
SQ = WIDTH // BOARD_SIZE          # square size in pixels
FPS = 60

# Depth for alpha-beta search (increase for stronger AI, slower moves)
AI_DEPTH = 3

# Colours  (R, G, B)
C_LIGHT      = (240, 217, 181)
C_DARK       = (181, 136,  99)
C_SELECT     = (255, 215,   0)    # gold highlight
C_VALID      = ( 50, 205,  50)    # green dot
C_LAST_MOVE  = (100, 149, 237)    # cornflower blue
C_BG         = ( 22,  21,  18)
C_TEXT_LIGHT = (240, 235, 220)
C_TEXT_DARK  = ( 80,  75,  65)
C_PANEL_BG   = ( 35,  33,  28)
C_ACCENT     = (200, 160,  60)

# Piece codes  (positive = White, negative = Black)
EMPTY = 0
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = 1, 2, 3, 4, 5, 6

PIECE_VALUES = {PAWN: 100, KNIGHT: 320, BISHOP: 330, ROOK: 500, QUEEN: 900, KING: 20000}

PIECE_UNICODE = {
    (KING,   True):  '♔', (QUEEN,  True):  '♕',
    (ROOK,   True):  '♖', (BISHOP, True):  '♗',
    (KNIGHT, True):  '♘', (PAWN,   True):  '♙',
    (KING,   False): '♚', (QUEEN,  False): '♛',
    (ROOK,   False): '♜', (BISHOP, False): '♝',
    (KNIGHT, False): '♞', (PAWN,   False): '♟',
}

# ─────────────────────────────────────────────
# PIECE-SQUARE TABLES  (from White's perspective)
# ─────────────────────────────────────────────
PST = {
    PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0,
    ],
    KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50,
    ],
    BISHOP: [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20,
    ],
    ROOK: [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         0,  0,  0,  5,  5,  0,  0,  0,
    ],
    QUEEN: [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20,
    ],
    KING: [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20,
    ],
}

# ─────────────────────────────────────────────
# BOARD REPRESENTATION
# ─────────────────────────────────────────────
def initial_board():
    """8×8 list of (piece_type, is_white) or None."""
    b = [[None]*8 for _ in range(8)]
    order = [ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP, KNIGHT, ROOK]
    for c in range(8):
        b[0][c] = (order[c], False)
        b[1][c] = (PAWN, False)
        b[6][c] = (PAWN, True)
        b[7][c] = (order[c], True)
    return b

# ─────────────────────────────────────────────
# MOVE GENERATION
# ─────────────────────────────────────────────
def in_bounds(r, c):
    return 0 <= r < 8 and 0 <= c < 8

def raw_moves(board, r, c, state):
    """Generate pseudo-legal moves for piece at (r,c)."""
    piece = board[r][c]
    if piece is None:
        return []
    pt, white = piece
    moves = []

    def slide(dr, dc):
        nr, nc = r+dr, c+dc
        while in_bounds(nr, nc):
            target = board[nr][nc]
            if target is None:
                moves.append((nr, nc))
            elif target[1] != white:
                moves.append((nr, nc)); break
            else:
                break
            nr += dr; nc += dc

    def step(squares):
        for nr, nc in squares:
            if in_bounds(nr, nc):
                target = board[nr][nc]
                if target is None or target[1] != white:
                    moves.append((nr, nc))

    if pt == PAWN:
        direction = -1 if white else 1
        start_row = 6 if white else 1
        # Forward
        nr = r + direction
        if in_bounds(nr, c) and board[nr][c] is None:
            moves.append((nr, c))
            if r == start_row and board[r + 2*direction][c] is None:
                moves.append((r + 2*direction, c))
        # Captures
        for dc in [-1, 1]:
            nc = c + dc
            if in_bounds(nr, nc):
                target = board[nr][nc]
                if target and target[1] != white:
                    moves.append((nr, nc))
                # En passant
                ep = state.get('en_passant')
                if ep and (nr, nc) == ep:
                    moves.append((nr, nc))

    elif pt == KNIGHT:
        step([(r+dr, c+dc) for dr,dc in
              [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]])

    elif pt == BISHOP:
        for d in [(-1,-1),(-1,1),(1,-1),(1,1)]: slide(*d)

    elif pt == ROOK:
        for d in [(-1,0),(1,0),(0,-1),(0,1)]: slide(*d)

    elif pt == QUEEN:
        for d in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]: slide(*d)

    elif pt == KING:
        step([(r+dr, c+dc) for dr,dc in
              [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]])
        # Castling
        cr = state.get('castling_rights', {})
        side = 'white' if white else 'black'
        row = 7 if white else 0
        if r == row and c == 4:
            if cr.get(f'{side}_king') and board[row][5] is None and board[row][6] is None:
                moves.append((row, 6))
            if cr.get(f'{side}_queen') and all(board[row][cc] is None for cc in [1,2,3]):
                moves.append((row, 2))

    return moves

def find_king(board, white):
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p and p == (KING, white):
                return (r, c)
    return None

def is_attacked(board, r, c, by_white):
    """Is square (r,c) attacked by any piece of colour by_white?"""
    dummy_state = {'en_passant': None, 'castling_rights': {}}
    for br in range(8):
        for bc in range(8):
            p = board[br][bc]
            if p and p[1] == by_white:
                if (r, c) in raw_moves(board, br, bc, dummy_state):
                    return True
    return False

def apply_move(board, state, fr, fc, tr, tc):
    """Return (new_board, new_state) without modifying originals."""
    b = copy.deepcopy(board)
    s = copy.deepcopy(state)
    piece = b[fr][fc]
    pt, white = piece
    captured = b[tr][tc]

    # En passant capture
    ep = s.get('en_passant')
    if pt == PAWN and ep and (tr, tc) == ep:
        cap_r = fr  # captured pawn row
        b[cap_r][tc] = None

    # Move piece
    b[tr][tc] = piece
    b[fr][fc] = None

    # Castling rook move
    row = 7 if white else 0
    cr = s.get('castling_rights', {})
    side = 'white' if white else 'black'
    if pt == KING:
        cr[f'{side}_king'] = False
        cr[f'{side}_queen'] = False
        if abs(tc - fc) == 2:
            if tc == 6:
                b[row][5] = b[row][7]; b[row][7] = None
            else:
                b[row][3] = b[row][0]; b[row][0] = None

    if pt == ROOK:
        if fc == 0: cr[f'{side}_queen'] = False
        if fc == 7: cr[f'{side}_king'] = False

    # Pawn promotion (auto-queen)
    if pt == PAWN and (tr == 0 or tr == 7):
        b[tr][tc] = (QUEEN, white)

    # Update en passant
    if pt == PAWN and abs(tr - fr) == 2:
        s['en_passant'] = ((fr + tr)//2, fc)
    else:
        s['en_passant'] = None

    s['castling_rights'] = cr
    s['turn'] = not s['turn']
    return b, s

def legal_moves(board, state, white):
    """All legal moves for colour white: list of (fr, fc, tr, tc)."""
    moves = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p and p[1] == white:
                for tr, tc in raw_moves(board, r, c, state):
                    nb, ns = apply_move(board, state, r, c, tr, tc)
                    kr = find_king(nb, white)
                    if kr and not is_attacked(nb, kr[0], kr[1], not white):
                        moves.append((r, c, tr, tc))
    return moves

# ─────────────────────────────────────────────
# EVALUATION
# ─────────────────────────────────────────────
def evaluate(board):
    score = 0
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p:
                pt, white = p
                val = PIECE_VALUES[pt]
                idx = r*8+c if not white else (7-r)*8+c
                pst_bonus = PST.get(pt, [0]*64)[idx]
                sign = 1 if white else -1
                score += sign * (val + pst_bonus)
    return score

# ─────────────────────────────────────────────
# ALPHA-BETA PRUNING
# ─────────────────────────────────────────────
def alpha_beta(board, state, depth, alpha, beta, maximising):
    white = maximising
    moves = legal_moves(board, state, white)

    if depth == 0 or not moves:
        return evaluate(board), None

    best_move = None
    if maximising:
        best = float('-inf')
        for m in moves:
            nb, ns = apply_move(board, state, *m)
            score, _ = alpha_beta(nb, ns, depth-1, alpha, beta, False)
            if score > best:
                best = score; best_move = m
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best, best_move
    else:
        best = float('inf')
        for m in moves:
            nb, ns = apply_move(board, state, *m)
            score, _ = alpha_beta(nb, ns, depth-1, alpha, beta, True)
            if score < best:
                best = score; best_move = m
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best, best_move

# ─────────────────────────────────────────────
# PYGAME INTERFACE
# ─────────────────────────────────────────────
def draw_board(surface, board, selected, valid_squares, last_move, font_piece, flip=False):
    for r in range(8):
        for c in range(8):
            dr = 7-r if flip else r
            dc = 7-c if flip else c
            light = (dr + dc) % 2 == 0
            colour = C_LIGHT if light else C_DARK

            # Last move highlight
            if last_move and ((r, c) == (last_move[0], last_move[1]) or
                               (r, c) == (last_move[2], last_move[3])):
                colour = C_LAST_MOVE

            # Selection highlight
            if selected and (r, c) == selected:
                colour = C_SELECT

            x, y = c*SQ, r*SQ
            pygame.draw.rect(surface, colour, (x, y, SQ, SQ))

            # Valid move dots
            if (r, c) in valid_squares:
                cx, cy = x + SQ//2, y + SQ//2
                pygame.draw.circle(surface, C_VALID, (cx, cy), SQ//8)

            # Piece
            p = board[r][c]
            if p:
                sym = PIECE_UNICODE[(p[0], p[1])]
                txt = font_piece.render(sym, True, (255,255,255) if not p[1] else (20,20,20))
                shadow = font_piece.render(sym, True, (0,0,0) if not p[1] else (200,200,200))
                surface.blit(shadow, (x + SQ//2 - txt.get_width()//2 + 2,
                                      y + SQ//2 - txt.get_height()//2 + 2))
                surface.blit(txt,    (x + SQ//2 - txt.get_width()//2,
                                      y + SQ//2 - txt.get_height()//2))

def draw_coordinates(surface, font_label, flip=False):
    files = 'abcdefgh'
    ranks = '87654321'
    if flip:
        files = files[::-1]
        ranks = ranks[::-1]
    for i in range(8):
        lbl_f = font_label.render(files[i], True, C_DARK if i%2==0 else C_LIGHT)
        lbl_r = font_label.render(ranks[i], True, C_DARK if i%2!=0 else C_LIGHT)
        surface.blit(lbl_f, (i*SQ + 4, HEIGHT - 18))
        surface.blit(lbl_r, (4, i*SQ + 4))

def draw_panel(surface, state, ai_on, status_msg, font_ui, font_small):
    # No side panel — we draw a bottom bar
    bar = pygame.Rect(0, HEIGHT, WIDTH, 60)
    # (panel is below board but window height is HEIGHT+60)
    pygame.draw.rect(surface, C_PANEL_BG, bar)
    turn_txt = "WHITE to move" if state['turn'] else "BLACK to move (AI)" if ai_on else "BLACK to move"
    t1 = font_ui.render(turn_txt, True, C_ACCENT)
    surface.blit(t1, (16, HEIGHT + 8))
    keys_txt = "R=Reset  U=Undo  A=AI  ESC=Quit"
    t2 = font_small.render(keys_txt, True, C_TEXT_LIGHT)
    surface.blit(t2, (16, HEIGHT + 34))
    if status_msg:
        ts = font_ui.render(status_msg, True, (220, 80, 80))
        surface.blit(ts, (WIDTH//2, HEIGHT + 8))
    ai_lbl = font_small.render(f"AI: {'ON' if ai_on else 'OFF'}  Depth:{AI_DEPTH}", True,
                                (80,200,80) if ai_on else (150,150,150))
    surface.blit(ai_lbl, (WIDTH - 180, HEIGHT + 34))

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT + 60))
    pygame.display.set_caption("Chess AI – Alpha-Beta Pruning")
    clock = pygame.time.Clock()

    # Fonts
    font_piece  = pygame.font.SysFont("segoeuisymbol", int(SQ * 0.72))
    font_ui     = pygame.font.SysFont("georgia", 18, bold=True)
    font_small  = pygame.font.SysFont("consolas", 14)
    font_label  = pygame.font.SysFont("consolas", 13)

    def reset():
        return {
            'board': initial_board(),
            'state': {
                'turn': True,           # True = White
                'en_passant': None,
                'castling_rights': {
                    'white_king': True, 'white_queen': True,
                    'black_king': True, 'black_queen': True,
                }
            },
            'history': [],
            'selected': None,
            'valid_squares': [],
            'last_move': None,
            'status': '',
            'ai_on': True,
            'ai_thinking': False,
        }

    game = reset()

    def get_square(mx, my):
        c = mx // SQ
        r = my // SQ
        if 0 <= r < 8 and 0 <= c < 8:
            return (r, c)
        return None

    def check_game_over():
        white = game['state']['turn']
        moves = legal_moves(game['board'], game['state'], white)
        if not moves:
            kr = find_king(game['board'], white)
            if kr and is_attacked(game['board'], kr[0], kr[1], not white):
                game['status'] = "CHECKMATE – " + ("Black wins!" if white else "White wins!")
            else:
                game['status'] = "STALEMATE – Draw!"
            return True
        return False

    running = True
    while running:
        clock.tick(FPS)

        # AI move
        if (game['ai_on'] and not game['state']['turn'] and
                not game['status'] and not game['ai_thinking']):
            game['ai_thinking'] = True
            _, move = alpha_beta(game['board'], game['state'],
                                  AI_DEPTH, float('-inf'), float('inf'), False)
            if move:
                game['history'].append((copy.deepcopy(game['board']),
                                         copy.deepcopy(game['state'])))
                game['board'], game['state'] = apply_move(game['board'], game['state'], *move)
                game['last_move'] = move
                check_game_over()
            game['ai_thinking'] = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    game = reset()
                elif event.key == pygame.K_a:
                    game['ai_on'] = not game['ai_on']
                    game['status'] = ''
                elif event.key == pygame.K_u:
                    if game['history'] and not game['ai_thinking']:
                        saved = game['history'].pop()
                        # Undo two half-moves so it stays player's turn
                        if game['ai_on'] and game['history']:
                            game['board'], game['state'] = game['history'].pop()
                        else:
                            game['board'], game['state'] = saved
                        game['selected'] = None
                        game['valid_squares'] = []
                        game['last_move'] = None
                        game['status'] = ''

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game['status'] or game['ai_thinking']:
                    continue
                if not game['state']['turn'] and game['ai_on']:
                    continue  # AI's turn
                sq = get_square(*event.pos)
                if sq is None:
                    continue
                r, c = sq

                if game['selected']:
                    if (r, c) in game['valid_squares']:
                        game['history'].append((copy.deepcopy(game['board']),
                                                 copy.deepcopy(game['state'])))
                        fr, fc = game['selected']
                        game['board'], game['state'] = apply_move(
                            game['board'], game['state'], fr, fc, r, c)
                        game['last_move'] = (fr, fc, r, c)
                        game['selected'] = None
                        game['valid_squares'] = []
                        check_game_over()
                    else:
                        # Re-select
                        p = game['board'][r][c]
                        if p and p[1] == game['state']['turn']:
                            game['selected'] = (r, c)
                            moves = legal_moves(game['board'], game['state'], p[1])
                            game['valid_squares'] = [(tr, tc) for fr2,fc2,tr,tc in moves
                                                      if fr2==r and fc2==c]
                        else:
                            game['selected'] = None
                            game['valid_squares'] = []
                else:
                    p = game['board'][r][c]
                    if p and p[1] == game['state']['turn']:
                        game['selected'] = (r, c)
                        moves = legal_moves(game['board'], game['state'], p[1])
                        game['valid_squares'] = [(tr, tc) for fr,fc,tr,tc in moves
                                                  if fr==r and fc==c]

        # ── Draw ──
        screen.fill(C_BG)
        draw_board(screen, game['board'], game['selected'],
                   game['valid_squares'], game['last_move'], font_piece)
        draw_coordinates(screen, font_label)
        draw_panel(screen, game['state'], game['ai_on'], game['status'], font_ui, font_small)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
