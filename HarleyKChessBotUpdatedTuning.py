import random
import copy
import math
import numpy as np

import cProfile

import time

'''
How to make it even stronger:
-Fix the square control formula by adding a pawn to each side, thereby hopefully providing a disincentive for the queen to come out early
-Tactics! It regularly falls for discoveries and stuff like that.
-double pinConstant, halve legalMoves constant, halve squareControl constant
-Quinscience search is necessary!

BUG: Obviously the search algorithm is broken. You're gonna have to debug it, i.e. find out why it is changing its mind to worse options rather than better ones
More depth isn't always better, but may be if you can fix this bug.

'''

searchWidth = 100  #We'll use a local variable

#Also TODO: Simplify the game generation by using a for loop which incorporates both white's and black's move.


'''
This AI is designed to play chess just like I would

It has several components that give it its skill:

Piece values (average mobility):

- King - 100000pts
- Queen - 9pts
- Rook - 5pts
- Bishop - 3.4pts
- Knight - 3.1pts
- Pawn - [1, 1.2, 1.5, 2, 3, 5, 9]pts for rows 2-8

Mobility multipliers:

- King - unaffected (Max = 8 squares)
- Queen - 0.5x-1.5x (Max = 27 squares)
- Rook - 0.5x-1.5x (Max = 14 squares)
- Bishop - 0.5x-1.5x (Max = 13 squares)
- Knight - 0.25x-1.75x (Max = 8 squares, but it really does matter)
- Pawn - 0.5x-2.5x (Max = 4 squares, assuming you can move a pawn 2 squares on the first move. Having 1 legal move is the norm.)

Square control

- King - 0.333pts
- Everything else is 1/OriginalPieceValue

- Half points everytime there is an obstacle in the way. E.g. a rook blocked by a pawn only half-controls the square beyond that, and only a quarter if there are two obstacles in the line of sight.
- Sum up each square of the board to determine the final result.

Domination = (WhitePoints/WhitePoints+BlackPoints) for each square. Centre squares are worth double (or whatever the centreFactor is for that).
- Any square near the king is multiplied by the kingSafetyFactor (maybe 3x).

Tactical control
- We'll implement this last, since it heavily depends on whose turn it is. No need to overcomplicate
- For now, the general jist is that attacking a piece is good.
- AttackBonus += 0.1 * AttackedPieceValue/AttackingPieceValue
- Make this too high, and there will be more focus on attacking, but less on winning material.

TotalEval = WhiteEval/BlackEval
WhiteEval = Sum[(Piece Values * Mobility multipliers) + Square control + Tactical control]

Bonus Stuff
- Endgame tablebase thingy: This is important. One strategy is to trade down until completely winning, then chase the king to the corner with a new evaluation function, and avoiding stalemate!
- Minimax: 5 ply but only considering the 'best move', captures and checks.
- Coaching heirachy: King safety is mentioned, followed by centre control, and who the coach thinks is winning.
- Opening database: To make it seem like it's actually me.
- Some form of castling incentive. Literally just adding a point to the team that is castled may help.


REPRESENTATION OF THE BOARD

- Board 0: The main board, which consists of the numbers between 0 and 12.
  0 represents blank, 1-6 represents the white pieces (P,N,B,R,Q,K), and 7-12 represents the black pieces. Use % to avoid if statements

- Board 1: 
    Line 0: En passant co-ordinates stored at [0][0], [1][0] universally, with [9][9] if blank
    Line 1: Has the king moved at [0][1] for white, and [4][1] for black, stored as a 1 or 0 for true or false
    Line 2: Is king castled, at [0][2] for white and [4][2] for black
    Line 3: Castling rights, at [0][3] and [1][3] for white for 0-0-0 and 0-0 respectively, then at [4][3] and [5][3] for black.




'''
def convertEvaluation(evaluation):
    return round(math.log(evaluation,2)*20,5)


def generateBitBoard(newBoard): #converts the board representation into a 'bitboard', which should save tonnes of memory and efficiency
    bitBoard = np.zeros((2, 8, 8))
    bitBoard = bitBoard.astype('u1')


    for y in range(8):
        for x in range(8):
            #update each bit based on the piece that occupies it
            pieceLabel = 0
            if testBoard[x][y][0] == '-':
                pieceLabel = 0
            else:
                if testBoard[x][y][1] == "Black":
                    pieceLabel = 6
                pieceLabel += pieceOrder[testBoard[x][y][0]] + 1
            bitBoard[0][x][y] = pieceLabel



def printBoard(testBoard): #I can live with this still being like this, as long as it isn't called frequently during recursion
    print(board[0])
    '''for y in range(8):
        for x in range(8):
            print([testBoard[0][x][7 - y]], end = "")
        print("      ", end = "")
        for x in range(8):
            print([testBoard[0][x][7 - y]], end = "")
        print()'''

#TODO: This code is inefficient. Is the Castling and en passant information being transferred correctly?
def makeMove(move, testBoard, colour): #for all moves not on the main board


    if colour == "White":
        yTest = 0
        colourTurn = 0
        pieceLabel = 0
    else:
        yTest = 7
        colourTurn = 1
        pieceLabel = 6

    piece = move[0]

    #Find the bitboard representation for the piece/colour
    if piece == '-':
        pieceLabel = 0
    else:
        pieceLabel += pieceOrder[piece] + 1


    #check for en passant, and if it is, clear the captured pawn
    if piece == 'P' and move[2] == 'x':
        if testBoard[0][move[3][0]][move[3][1]] == 0: #destination square is empty so it must be en passant
            #0 means empty in our new representation.

            #clear the captured pawn
            testBoard[0][move[3][0]][move[1][1]] = 0

    if piece == 'K': #If the king moves, you can't castle
        testBoard[1][colourTurn*4][3] = 0 #Can't castle queenside from now on
        testBoard[1][colourTurn*4 + 1][3] = 0 #Can't castle kingside from now on
        testBoard[1][colourTurn*4][1] = 1 #The king has moved
        if abs(move[1][0] - move[3][0]) == 2: #if castling
            testBoard[1][colourTurn*4][2] = 1 #The king is castled now

    if piece == 'R': #If the rook moves, you can't castle in that direction
        if move[1][0] == 0: #if x == 0, you can't castle queenside
            testBoard[1][colourTurn*4][3] = 0 #Can't castle queenside from now on
        else:
            testBoard[1][colourTurn*4 + 1][3] = 0 #Can't castle kingside from now on

    if piece == 'P' and abs(move[1][1]-move[3][1])==2: #If pawn moves 2 squares, en passant is possible next move
        x = move[1][0]
        y = int((move[1][1] + move[3][1])/2)
        testBoard[1][0][0] = x #Entering en passant co-ordinates
        testBoard[1][1][0] = y
    else:
        testBoard[1][0][0] = 9 #En passant is now impossible
        testBoard[1][1][0] = 9

    #clear the starting square
    testBoard[0][move[1][0]][move[1][1]] = 0

    #put the piece on the new square
    testBoard[0][move[3][0]][move[3][1]] = pieceLabel

    if piece == 'K':
        #the king has moved, so let's update that
        testBoard[1][colourTurn*4][1] = 1

        if (move[1] == [4,0] and colour == "White") or (move[1] == [4,7] and colour == "Black"):
            #Possible that castling is being performed
            if move[3][0] == 2: #TODO: Debug to make sure this is working correctly (print the board after castling)

                #Castling queenside
                testBoard[1][colourTurn*4][2] = 1 #The king is now castled

                testBoard[1][colourTurn*4][3] = 1 #Can't castle queenside anymore
                testBoard[1][colourTurn*4 + 1][3] = 1 #Can't castle kingside anymore

                #clear the starting square
                testBoard[0][0][yTest] = 0

                #put the rook on the new square
                testBoard[0][3][yTest] = (pieceOrder['R'] + 1) + (colourTurn * 6)
                
            elif move[3][0] == 6:

                #Castling kingside
                testBoard[1][colourTurn*4][2] = 1 #The king is now castled

                testBoard[1][colourTurn*4][3] = 1 #Can't castle queenside anymore
                testBoard[1][colourTurn*4 + 1][3] = 1 #Can't castle kingside anymore

                #clear the starting square
                testBoard[0][7][yTest] = 0

                #put the piece on the new square
                testBoard[0][5][yTest] = (pieceOrder['R'] + 1) + (colourTurn * 6)

    #check pawn promotion, and if so, promote to a queen
    if move[0] == 'P':
        if (colour == "White" and move[3][1] == 7) or (colour == "Black" and move[3][1] == 0):
            testBoard[0][move[3][0]][move[3][1]] = (pieceOrder['Q'] + 1) + (colourTurn * 6)

    return testBoard
    
#this function makes a move on the board for the colour, then checks if that king is safe
def isKingInCheck(move, testBoard, colour):

    if colour == "White":
        otherColour = "Black"
    else:
        otherColour = "White"

    fakeTestBoard = [[[testBoard[i][j][k] for k in range(8)] for j in range(8)] for i in range(2)]

    #make test move 
    fakeTestBoard = makeMove(move, fakeTestBoard, colour)

    #check legal moves from otherColour's perspective, and return if the king gets hit.
    isCheck = calculateLegalMoves(otherColour, fakeTestBoard)[1]

    return isCheck

def printMove(turn, move):
    print(str(turn) + ". " + move[0]+chr(ord('`')+move[1][0]+1)
    +str(move[1][1]+1)+str(move[2])
    +chr(ord('`')+move[3][0]+1)+str(move[3][1]+1))

def inBounds(x,y):
    if x>=0 and x <= 7 and y>=0 and y<=7:
        return True
    else:
        return False

def findKingsAndQueens(colour, newBoard): #TODO: Rewrite using numpy, it'll run a lot quicker
    if colour == "White":
        pieceTranslation = 0
        antiPieceTranslation = 6
    else:
        pieceTranslation = 6
        antiPieceTranslation = 0
    
    kings = [[9,9],[9,9]]
    queens = [False, False]

    for x in range(8):
        for y in range(8):
            if newBoard[0][x][y] == pieceOrder['Q'] + 1 + pieceTranslation: #If queen of our colour
                queens[0] = True
            elif newBoard[0][x][y] == pieceOrder['Q'] + 1 + antiPieceTranslation: #If queen of their colour
                queens[1] = True
            if newBoard[0][x][y] == pieceOrder['K'] + 1 + pieceTranslation: #If king of our colour
                kings[0] = [x,y]
            elif newBoard[0][x][y] == pieceOrder['K'] + 1 + antiPieceTranslation: #If king of their colour:
                kings[1] = [x,y]
    return [kings, queens]

def isNearKing(square, king): #used to recognise when the king is in danger (e.g. a scary knight)
    if abs(square[0]-king[0]) < 2 and abs(square[1]-king[1]) < 2:
        return True
    else:
        return False

def calculateLegalMoves(colour, newBoard):
    evaluation = 0
    isCheck = False

    #[kings, queens] = findKingsAndQueens(colour, newBoard)
    #NOTE: kings is in co-ordinates; queens is in booleans

    #NOTE: Let's not worry about indirect attacks.
        #Reasoning: Imagine a bishop pinning a knight against a king. That's worth a lot more points than it should be.


    #I've resorted to storing the piece quantities, rather than the exact pieces.
    pieceValuesArray = [[0 for i in range(8)] for j in range(8)]

    #pieceValuesArray = np.zeros((8,8)) #don't change the data type yet, since this includes decimal values

    #For calculating tactics
    attackArray = [[[0 for k in range(6)] for j in range(8)] for i in range(8)]

    #attackArray = np.zeros((8,8,6))

    #We want as many squares as possible to be controlled by our team.
    #Bonus points for controlling squares near the king or in the centre 4
    #Controlling squares indirectly also counts (a bit)
    squareControl = [[0 for i in range(8)] for j in range(8)]
    
    #squareControl = np.zeros((8,8))

    legalMoves = []
    strongMoves = []

    if colour == "White":
        colourMult = 1
    else:
        colourMult = -1

    if colour == "White":
        startRow = 0
    else:
        startRow = 7

    if colour == "White":
        colourTurn = 0
        antiColourTurn = 1
    else:
        colourTurn = 1
        antiColourTurn = 0

    for x in range(8):
        for y in range(8):
            noOfLegalMoves = 0
            if newBoard[0][x][y] > (colourTurn * 6) and newBoard[0][x][y] < (colourTurn * 6) + 7:
                #We have found a piece of our colour that can move
                pieceLabel = newBoard[0][x][y]
                if pieceLabel == 0:
                    piece = 'P'
                else:
                    piece = orderPiece[int(pieceLabel - colourTurn*6 - 1)] 

                if piece == 'P':
                    pieceValuesArray[x][y] = pawnValues[startRow + colourMult*y]
                else:
                    pieceValuesArray[x][y] = pieceValuesStanding[piece]
    
                start = time.time()
                if piece == 'P': 
                    #Find pawn pushes
                    newX = x
                    newY = y+colourMult
                    if inBounds(newX,newY):
                        if newBoard[0][newX][newY] == 0:
                            legalMoves.append([piece, [x, y], '-', [newX, newY]]) 
                            #TODO: We're working with compound lists a lot. We should probably do something about that
                            noOfLegalMoves += 1
                            if (newY == 2 and colour == "White") or (newY == 5 and colour == "Black"): 
                                newY = newY+colourMult
                                if inBounds(newX,newY):
                                    if newBoard[0][newX][newY] == 0:
                                        legalMoves.append([piece, [x, y], '-', [newX, newY]])
                                        noOfLegalMoves += 1
                    #Find pawn captures
                    newY = y + colourMult
                    newX = x - 1
                    if inBounds(newX,newY):
                        if newBoard[0][newX][newY] > (colourTurn * 6) and newBoard[0][newX][newY] < (colourTurn * 6) + 7: #if our colour
                            attackArray[newX][newY][pieceOrder[piece]] += 1 #defending

                        elif newBoard[0][newX][newY] > (antiColourTurn * 6) and newBoard[0][newX][newY] < (antiColourTurn * 6) + 7: #if capturing piece
                            legalMoves.append([piece, [x, y], 'x', [newX, newY]])
                            strongMoves.append([piece, [x, y], 'x', [newX, newY]])
                            noOfLegalMoves += 1
                            attackArray[newX][newY][pieceOrder[piece]] += 1
                            squareControl[newX][newY] += 1.0/pieceValues[piece]
                            
                            if newBoard[0][newX][newY] == pieceOrder['K'] + 1 + (antiColourTurn*6): #TODO: I reckon we can calculate check using an easier method - by using a threats array
                                isCheck = True
                        
                    newX = x + 1
                    if inBounds(newX,newY):
                        if newBoard[0][newX][newY] > (colourTurn * 6) and newBoard[0][newX][newY] < (colourTurn * 6) + 7: #if our colour
                            attackArray[newX][newY][pieceOrder[piece]] += 1 #defending
                        elif newBoard[0][newX][newY] > (antiColourTurn * 6) and newBoard[0][newX][newY] < (antiColourTurn * 6) + 7: #if capturing piece
                            legalMoves.append([piece, [x, y], 'x', [newX, newY]])
                            strongMoves.append([piece, [x, y], 'x', [newX, newY]])
                            noOfLegalMoves += 1
                            attackArray[newX][newY][pieceOrder[piece]] += 1
                            squareControl[newX][newY] += 1.0/pieceValues[piece]

                            if newBoard[0][newX][newY] == pieceOrder['K'] + 1 + (antiColourTurn*6): #if piece is king of opposite colour
                                isCheck = True

                    #Find en passant captures
                    newY = y + colourMult
                    newX = x - 1
                    if inBounds(newX,newY) and newBoard[1][0][0] == newX and newBoard[1][1][0] == newY: 
                        #print("enPassant")
                        #if in bounds and en passant square is correct
                        if newBoard[0][newX][newY] == 0: #if capturing en passant
                            legalMoves.append([piece, [x, y], 'x', [newX, newY]])
                            strongMoves.append([piece, [x, y], 'x', [newX, newY]])
                            noOfLegalMoves += 1
                            attackArray[newX][newY][pieceOrder[piece]] += 1
                            squareControl[newX][newY] += 1.0/pieceValues[piece]
                            if newBoard[0][newX][newY] == pieceOrder['K'] + 1 + (antiColourTurn*6): #if piece is king of opposite colour
                                isCheck = True
                        
                    newX = x + 1
                    if inBounds(newX,newY) and newBoard[1][0][0] == newX and newBoard[1][1][0] == newY: 
                        #print("enPassant")
                        #if in bounds and en passant square is correct
                        if newBoard[0][newX][newY] == 0: #if capturing en passant
                            legalMoves.append([piece, [x, y], 'x', [newX, newY]])
                            strongMoves.append([piece, [x, y], 'x', [newX, newY]])
                            noOfLegalMoves += 1
                            attackArray[newX][newY][pieceOrder[piece]] += 1
                            squareControl[newX][newY] += 1.0/pieceValues[piece]
                            if newBoard[0][newX][newY] == pieceOrder['K'] + 1 + (antiColourTurn*6): #if piece is king of opposite colour
                                isCheck = True
                    

                if piece == 'N' or piece == 'K': #TODO: Change lists into a numpy array, for efficiency
                    if piece == 'N':
                        newXs = [1, 2, 2, 1, -1, -2, -2, -1]
                        newYs = [2, 1, -1, -2, -2, -1, 1, 2]
                    else: #TODO: obviously the king is going to make a lot of illegal moves. It can't move to an attacked square.
                        #my plan is to calculate all legal moves from the opposing colour first.
                            #any destination square will be added to the 'targetedSquares' matrix for that colour.
                        newXs = [-1, -1, -1, 0, 0, 1, 1, 1]
                        newYs = [-1, 0, 1, -1, 1, -1, 0, 1]

                    #Let's provide some castling options:
                    if piece == 'K' and x == 4:
                        if (colour == "White" and y == 0) or (colour == "Black" and y == 7): #King is in the right place
                            if (colour == "White" and newBoard[0][0][0] == pieceOrder['R'] + 1) or (colour == "Black" and newBoard[0][0][7]==pieceOrder['R'] + 7):
                                #Queenside castling may be possible
                                newX = x - 2
                                newY = y
                                legalMoves.append([piece, [x, y], '-', [newX, newY]])
                                noOfLegalMoves += 1
                            if (colour == "White" and newBoard[0][7][0] == pieceOrder['R'] + 1) or (colour == "Black" and newBoard[0][7][7]==pieceOrder['R'] + 7):
                                #Kingside castling may be possible
                                newX = x + 2
                                newY = y
                                legalMoves.append([piece, [x, y], '-', [newX, newY]])
                                noOfLegalMoves += 1
                    for i in range(8):
                        newX = x + newXs[i]
                        newY = y + newYs[i]
                        if inBounds(newX,newY):
                            
                            if newBoard[0][newX][newY] == 0: #not capturing

                                legalMoves.append([piece, [x, y], '-', [newX, newY]])
                                noOfLegalMoves += 1
                                attackArray[newX][newY][pieceOrder[piece]] += 1 #still could be defending
                                squareControl[newX][newY] += 1.0/pieceValues[piece]
                            elif newBoard[0][newX][newY] > (colourTurn * 6) and newBoard[0][newX][newY] < (colourTurn * 6) + 7: #if our colour (defending)
                                attackArray[newX][newY][pieceOrder[piece]] += 1
                                squareControl[newX][newY] += 1.0/pieceValues[piece]
                            elif newBoard[0][newX][newY] > (antiColourTurn * 6) and newBoard[0][newX][newY] < (antiColourTurn * 6) + 7: #if capturing piece

                                legalMoves.append([piece, [x, y], 'x', [newX, newY]])
                                strongMoves.append([piece, [x, y], 'x', [newX, newY]])
                                noOfLegalMoves += 1
                                attackArray[newX][newY][pieceOrder[piece]] += 1
                                squareControl[newX][newY] += 1.0/pieceValues[piece]
                                if newBoard[0][newX][newY] == pieceOrder['K'] + 1 + (antiColourTurn*6): #if piece is king of opposite colour
                                    isCheck = True
                    


                if piece == 'B' or piece == 'R' or piece == 'Q':
                    if piece == 'B':
                        pieceValue = 3.4
                        newXs = [-1, -1, 1, 1]
                        newYs = [-1, 1, -1, 1]
                    elif piece == 'R':
                        pieceValue = 5
                        newXs = [-1, 0, 0, 1]
                        newYs = [0, -1, 1, 0]
                    elif piece == 'Q':
                        pieceValue = 9
                        newXs = [-1, -1, -1, 0, 0, 1, 1, 1]
                        newYs = [-1, 0, 1, -1, 1, -1, 0, 1]
                    for i in range(len(newXs)):
                        newX = x
                        newY = y
                        inLine = 1.0
                        for move in range(8):
                            newX += newXs[i]
                            newY += newYs[i]
                            if inBounds(newX,newY):
                                if newBoard[0][newX][newY] == 0: #not capturing
                                    if inLine == 1:
                                        legalMoves.append([piece, [x, y], '-', [newX, newY]])
                                        noOfLegalMoves += 1
                                        attackArray[newX][newY][pieceOrder[piece]] += 1 #still could be defending
                                        squareControl[newX][newY] += 1.0/pieceValues[piece]
                                    
                                elif newBoard[0][newX][newY] > (colourTurn * 6) and newBoard[0][newX][newY] < (colourTurn * 6) + 7: #if our colour (defending)
                                    if inLine == 1:
                                        attackArray[newX][newY][pieceOrder[piece]] += 1
                                        squareControl[newX][newY] += 1.0/pieceValues[piece]
                                    inLine /= 2 #since you can't jump over your pieces
                                
                                else: #capturing
                                    if inLine == 1:
                                        legalMoves.append([piece, [x, y], 'x', [newX, newY]])
                                        strongMoves.append([piece, [x, y], 'x', [newX, newY]])
                                        noOfLegalMoves += 1
                                        attackArray[newX][newY][pieceOrder[piece]] += 1
                                        squareControl[newX][newY] += 1.0/pieceValues[piece]
                                        if newBoard[0][newX][newY] == pieceOrder['K'] + 1 + (antiColourTurn*6): #if piece is king of opposite colour
                                            isCheck = True
                                    else: #Look at indirect attacks
                                        if newBoard[0][newX][newY] != pieceOrder['K'] + 1 + (antiColourTurn*6): #if piece is NOT a king of the opposite colour
                                            #Figure out the piece first
                                            testIndex = int(newBoard[0][newX][newY] - 1 - (colourTurn * 6))
                                            if testIndex > 5:
                                                testIndex -= 6
                                            testPiece = orderPiece[testIndex]
                                            evaluation += pieceValues[testPiece] * pinConstant * inLine
                                        else:
                                            evaluation += 9 * pinConstant * inLine #don't overvalue king pins
                                    inLine /= 4 #I find pins less scary than discovered attacks
                            else:
                                break
                #NOTE: This system is not perfect, as any 'legal' move (including some that may turn out
                #to be illegal), will be included.
                if piece == 'P': 
                    if x>1 and x<6: #If the pawn is more or less in the centre
                        evaluation += (pawnValuesInner[startRow + colourMult*y]) * (0.9 + 0.1 * noOfLegalMoves)
                    else:
                        evaluation += (pawnValues[startRow + colourMult*y]) * (0.9 + 0.1 * noOfLegalMoves)
                if piece == 'N':
                    evaluation += pieceValues[piece] * (0.875 + (0.25/8) * noOfLegalMoves)
                if piece == 'B':
                    evaluation += pieceValues[piece] * (0.94 + (0.12/13) * noOfLegalMoves)
                if piece == 'R':
                    evaluation += pieceValues[piece] * (0.94 + (0.12/14) * noOfLegalMoves)
                if piece == 'Q':
                    evaluation += pieceValues[piece] * (0.9985 + (0.003/27) * noOfLegalMoves)
    #NOTE: attackArray is probably returning correctly. Let's look more into the 'winnings' calculations.
    return [legalMoves, isCheck, evaluation, pieceValuesArray, attackArray, squareControl, strongMoves]

def minimaxSearch(newBoard, depth, testTurnNo, alpha, beta, extraCost, limitedDepth):

    newExtraCost = extraCost
    #if depth >= 10:
        #print("Huge Depth")
    searchWidth = 20
    pawnMult = 1 - testTurnNo*2
    colour = colours[testTurnNo]
    if colour == "White":
        otherColour = "Black"
    else:
        otherColour = "White"

    #newBoard = np.copy(testBoard) #copying a numpy array should be quick (hopefully)
    #stuff = cProfile.run('calculateLegalMoves(colour, newBoard)')
    stuff = calculateLegalMoves(colour, newBoard)
    legalMoves = stuff[0]

    rawEvals = []
    rawMoves = []

    confirmedLegalMoves = []
    originalExtraCost = extraCost
    for move in legalMoves:
        originalExtraCost = extraCost
        piece = move[0]

        #newBoard = np.copy(testBoard) #copying a numpy array should be quick (hopefully)
        if move == [piece, [4, testTurnNo*7], '-', [2, testTurnNo*7]]:
            #try to castle queenside
            if newBoard[1][testTurnNo*4][3] == 1: #Can we legally castle queenside?
                #Are the squares clear?
                if newBoard[0][3][testTurnNo*7] == 0 and newBoard[0][2][testTurnNo*7] == 0 and newBoard[0][1][testTurnNo*7] == 0:
                    testMove = ['K', [4, testTurnNo*7], '-', [4, testTurnNo*7]] #cannot castle if in check!
                    if not isKingInCheck(testMove, newBoard, colour):
                        testMove = ['K', [4, testTurnNo*7], '-', [3, testTurnNo*7]]
                        if not isKingInCheck(testMove, newBoard, colour):
                            testMove = ['K', [3, testTurnNo*7], '-', [2, testTurnNo*7]] #Assuming the board is modified within the function
                            if not isKingInCheck(testMove, newBoard, colour):
                                confirmedLegalMoves.append(move)

        elif move == [piece, [4, testTurnNo*7], '-', [6, testTurnNo*7]]:
            #try to castle kingside
            if newBoard[1][testTurnNo*4 + 1][3] == 1: #Can we legally castle kingside?
                #Are the squares clear?
                if newBoard[0][5][testTurnNo*7] == 0 and newBoard[0][6][testTurnNo*7] == 0:
                    testMove = ['K', [4, testTurnNo*7], '-', [4, testTurnNo*7]] #cannot castle if in check!
                    if not isKingInCheck(testMove, newBoard, colour):
                        testMove = ['K', [4, testTurnNo*7], '-', [5, testTurnNo*7]]
                        if not isKingInCheck(testMove, newBoard, colour):
                            testMove = ['K', [5, testTurnNo*7], '-', [6, testTurnNo*7]] #Assuming the board is modified within the function
                            if not isKingInCheck(testMove, newBoard, colour):
                                confirmedLegalMoves.append(move)

        elif not isKingInCheck(move, newBoard, colour):
            confirmedLegalMoves.append(move)

    #Let's add some tactics to scare away noobs
    if colour == "White":
        bestEval = -99999999
    else:
        bestEval = 99999999

    if len(confirmedLegalMoves) > 0:
        for move in confirmedLegalMoves:
            testBoard = [[[newBoard[i][j][k] for k in range(8)] for j in range(8)] for i in range(2)] #This should hopefully work on a numpy array 
            
            #TODO: Check that enpassant is copying across correctly

            makeMove(move, testBoard, colour)
            #since we are using a pointer, we don't need to create a 2nd instance #TODO: Is this working correctly?

            [otherLegalMoves, fakeIsCheck, goodEval, goodPieces, goodAttack, goodSquareControl, nextStrongMoves] = calculateLegalMoves(colour, testBoard)
            [otherLegalMoves, fakeIsCheck, badEval, badPieces, badAttack, badSquareControl, otherStrongMoves] = calculateLegalMoves(otherColour, testBoard)
            #TODO: IMPORTANT: fix castling rights, and other stuff, so they update and recurse correctly

            '''if depth < maxDepth and (move in strongMoves): #or depth == 1 for proper search at lower level
                #We've found the move and board position, so let's look deeper
                [consideredMove, evaluation] = minimaxSearch(testBoard, depth + 1, 1 - testTurnNo, newEnPassant, newCastlingRights, newIsKingCastled, newHasKingMoved)
                #Now we are considering both searched moves and immediate moves    
                if (evaluation) > bestEval: #new best move
                    bestEval = evaluation
                    bestMove = move
            else:'''
            #But wait, there's more. Let's add tactical analysis!
            #just to be clear, bad = opponent (in this case, the human).

            for x in range(8):
                for y in range(8):

                    #Let's calculate the tactical advantages our side has first

                    goodIndex = 0
                    badIndex = 0
                    bestWinnings = 0
                    winnings = 0

                    pieceHolder = badPieces[x][y]
                    attackingResources = goodAttack[x][y]
                    defendingResources = badAttack[x][y]

                    
                    if badPieces[x][y] != 0: #there is a piece to attack, so we may get a bonus
                        indicator = 0
                        while(sum(attackingResources) > 0.1): #while there are attacking resources
                            indicator += 1
                            #Find our weakest attacking piece
                            for i in range(6):
                                if attackingResources[goodIndex]==0:
                                    goodIndex += 1
                                    if goodIndex == 6:
                                        break #No more attacking resources left, we are done
                                else:
                                    break

                            if goodIndex == 6:
                                break #No more attacking resources left, we are done
                            else:
                                '''print("It's actually doing something")
                                print(move)
                                print(pieceHolder)
                                print(attackingResources)
                                print(defendingResources)'''
                                
                                winnings += pieceHolder
                                attackingResources[goodIndex] -= 1
                                if goodIndex == 5: #King's should not be captured
                                    pieceHolder = 20
                                elif goodIndex == 0: #better to use the actual pawn value
                                    pieceHolder = pawnValues[(y * pawnMult) + (testTurnNo * 7)]
                                else:
                                    pieceHolder = piecePlaceValues[goodIndex]

                                '''print(winnings)
                                print()'''

                            #Now it's our opponent's turn to defend  

                            #Find their weakest defending piece
                            for i in range(6):
                                if defendingResources[badIndex]==0:
                                    badIndex += 1
                                    if badIndex == 6:
                                        break #No more defensive resources left, we are essentially done
                                else:
                                    break

                            if badIndex == 6:
                                break #No more defensive resources left, we are essentially done
                            else: #capture the piece
                                winnings -= pieceHolder
                                defendingResources[badIndex] -= 1
                                if badIndex == 5: #King's should not be captured
                                    pieceHolder = 20
                                elif badIndex == 0: #better to use the actual pawn value
                                    pieceHolder = pawnValues[(y * pawnMult) + (testTurnNo * 7)]
                                else:
                                    pieceHolder = piecePlaceValues[badIndex]

                            if winnings > bestWinnings:
                                bestWinnings = winnings
                        if winnings > bestWinnings: #this code must also perform after everything is done :)
                            bestWinnings = winnings
                        if bestWinnings > badPieces[x][y]:
                            bestWinnings = badPieces[x][y] #We're not winning more than pieceHolder
                        if bestWinnings > 0:
                            '''print("yay, some actual winnings")
                            print(bestWinnings)
                            print(move)
                            print(x)
                            print(y)
                            
                            print(attackingResources)
                            print(defendingResources)
                            print(indicator)
                            print()'''

                        goodEval += 0.1 * bestWinnings #There is time for them to escape
                        
                    #Now, we need to calculate the opponent's attacks

                    
                    goodIndex = 0
                    badIndex = 0
                    bestWinnings = 0
                    winnings = 0

                    pieceHolder = goodPieces[x][y]
                    attackingResources = badAttack[x][y]
                    defendingResources = goodAttack[x][y]
                    #TODO: Why is there nothing in defendingResources
                    #(set a break point at indicator +=1 and repeatedly click continue)
                    if goodPieces[x][y] != 0: #there is a piece to attack, so they may get a bonus
                        indicator = 0
                        while(sum(attackingResources) > 0.1): #There are still attacking resources
                            indicator += 1
                            #Find their weakest attacking piece
                            for i in range(6):
                                if attackingResources[badIndex]==0:
                                    badIndex += 1
                                    if badIndex == 6:
                                        break #No more attacking resources left, we are done
                                else:
                                    break

                            if badIndex == 6:
                                break #No more attacking resources left, we are done
                            else:
                                winnings += pieceHolder
                                attackingResources[badIndex] -= 1
                                if badIndex == 5: #King's should not be captured
                                    pieceHolder = 20
                                elif badIndex == 0: #better to use the actual pawn value
                                    pieceHolder = pawnValues[(7 * testTurnNo) + (y * pawnMult)]
                                else:
                                    pieceHolder = piecePlaceValues[badIndex]

                            #Now it's our turn to defend  

                            #Find our weakest defending piece
                            for i in range(6):
                                if defendingResources[goodIndex]==0:
                                    goodIndex += 1
                                    if goodIndex == 6:
                                        break #No more defensive resources left, we are essentially done
                                else:
                                    break

                            if goodIndex == 6:
                                break #No more defensive resources left, we are essentially done
                            else: #capture the piece
                                winnings -= pieceHolder
                                defendingResources[goodIndex] -= 1
                                if goodIndex == 5: #Kings should not be captured
                                    pieceHolder = 20
                                elif goodIndex == 0: #better to use the actual pawn value
                                    pieceHolder = pawnValues[(y * pawnMult) + (testTurnNo * 7)]
                                else:
                                    pieceHolder = piecePlaceValues[goodIndex]

                            if winnings > bestWinnings:
                                bestWinnings = winnings
                        if winnings > bestWinnings: #this code must also perform after everything is done :)
                            bestWinnings = winnings
                        if bestWinnings > goodPieces[x][y]:
                            bestWinnings = goodPieces[x][y] #They're not winning more than pieceHolder
                        if bestWinnings > 3:
                            '''print(bestWinnings)
                            print(move)
                            print(x)
                            print(y)
                            
                            print(goodAttack)
                            print(badAttack)
                            print(indicator)
                            print()'''

                        badEval += 0.95 * bestWinnings #no time to escape

            #Don't forget about square control!
            overallPoints = 0
            [kings, queens] = findKingsAndQueens(colour, testBoard)

            for x in range(8):
                for y in range(8):
                    squareMult = 1
                    #I have added plus 1 to try to reward pawn control over queen control, when there is only one controlling piece
                    goodPoints = goodSquareControl[x][y] + 1 
                    badPoints = badSquareControl[x][y] + 1

                    if isNearKing([x,y],kings[1]) and goodPoints > badPoints:
                        squareMult = kingSafetyConstant
                    elif isNearKing([x,y],kings[0]) and badPoints > goodPoints:
                        squareMult = kingSafetyConstant
                    
                    if x in [3,4] and y in [3,4]:
                        squareMult *= centreConstant
                    
                    totalPoints = goodPoints + badPoints
                    if totalPoints != 0:
                        points = goodPoints/totalPoints
                        scaledPoints = 2*points - 1
                        overallPoints += scaledPoints
            
            if overallPoints > 0: #our side performed better
                goodEval += overallPoints * squareControlConstant
            else:
                badEval += overallPoints * squareControlConstant


            #We need an incentive for not moving the king if not castled
            #(assuming the other queen is on the board)
            #NOTE: This isn't applying to the current move. We'll have to do that seperately.
            if testBoard[1][testTurnNo*4][2] == 0: #if our king is castled
                if queens[1-testTurnNo] == True:
                    goodEval -= castlingCost
                    #TODO: Debug this using breakpoints
            if testBoard[1][4 - testTurnNo*4][2] == 0: #if their king is castled
                if queens[testTurnNo] == True:
                    badEval -= castlingCost



            #remove dividing by 0 possibilities
            if goodEval < 0.001:
                goodEval = 0.001
            if badEval < 0.001:
                badEval = 0.001
            
            

            evaluation = goodEval/badEval
            evaluation = convertEvaluation(evaluation)
            if colour == "Black":
                evaluation = -evaluation #for the other colour'''
                evaluation += 0.4 #since it's White's move
            else:
                evaluation -= 0.4 #since it's Black's move

            #if move not in strongMoves:
            rawMoves.append(move)
            rawEvals.append(evaluation)  

            #Now we are considering both searched moves and immediate moves    
            '''if move in strongMoves and depth == maxDepth:
                if (evaluation) > bestEval: #new best move
                    bestEval = evaluation
                    bestMove = move'''
        while limitedDepth + extraCost <= maxDepth: #I think we only want to apply this to depth = 1. Otherwise it will loop forever at depth 2+
            
            #We wanna tighten the evaluation difference allowed
            pruningConstant = 2 * 0.3**(limitedDepth - (depth + extraCost) - 1) 
            if limitedDepth - depth == 1: #if on the last iteration, search everything
                pruningConstant = 100

            #Reset best eval for every iteration
            if colour == "White":
                bestEval = -99999999
            else:
                bestEval = 99999999
            testRawEvals = [rawEvals[i] for i in range(len(rawEvals))] #Need to work with copies, as we are deleting elements
            testRawMoves = [rawMoves[i] for i in range(len(rawMoves))]  
            strongMoves = []
            #Testing out all strong moves
            #if depth + originalExtraCost <= maxDepth:
            moveRank = 0
            while len(strongMoves) < searchWidth:
                moveRank += 1
                if len(testRawEvals) == 0: #no more moves to look at
                    break
                if colour == "White":
                    bestIndex = testRawEvals.index(max(testRawEvals))
                else:
                    bestIndex = testRawEvals.index(min(testRawEvals))
                move = testRawMoves[bestIndex]
                strongMoves.append(move)
                testBoard = [[[newBoard[i][j][k] for k in range(8)] for j in range(8)] for i in range(2)] #Why are there so many copies of the board? lol

                makeMove(move, testBoard, colour) #don't wanna change any of the castling stuff here
                newExtraCost = originalExtraCost #TODO: Fix quintience search, so that it always calculates captures and checks first
                if moveRank == 1: #use this evaluation as a comparison point
                    testBestEval = testRawEvals[bestIndex]
                    if move[2] == 'x':
                        newExtraCost -= 0.5
                else:
                    if move[2] == 'x':
                        newExtraCost -= 0.5
                    if testRawEvals[bestIndex] == 0:
                        testRawEvals[bestIndex] = 0.001
                    if colour == "White":
                        evalDifference = testBestEval - rawEvals[bestIndex]
                    else:
                        evalDifference = rawEvals[bestIndex] - testBestEval
                    if depth + extraCost == 1 and limitedDepth == 2:
                        pruningConstant = 100 #basically, no pruning
                    costPrep = evalDifference * pruningConstant
                    if costPrep < 0:
                        #print("Cost is too low")
                        costPrep = 0
                    elif evalDifference > pruningConstant: #stop searching
                        if move[2] != 'x':
                            break
                        #print("Cost reduction")
                    #newExtraCost += costPrep
                    
                if (depth + extraCost) <= limitedDepth - 1: #Hopefully this works 
                    [consideredMove, evaluation] = minimaxSearch(testBoard, depth + 1, 1 - testTurnNo, alpha, beta, newExtraCost, limitedDepth)
                    

                    #WE NEED TO UPDATE THE RAW EVAL OF THAT MOVE, IN RAW_EVALS (NOT TEST_RAW_EVALS)
                    rawEvals[bestIndex] = evaluation
                    
                    if (evaluation > bestEval and colour == "White") or (evaluation < bestEval and colour == "Black"): #new best move
                        bestEval = evaluation
                        bestMove = move

                    if colour == "White":
                        alpha = max(alpha, evaluation)
                        if alpha >= beta:
                            #print(alpha)
                            #print(beta)
                            #print("White")
                            return [bestMove, bestEval]
                    else:
                        beta = min(beta, evaluation)
                        if alpha >= beta:
                            #print(alpha)
                            #print(beta)
                            #print("Black")
                            return [bestMove, bestEval]
                else: #Use calculated evaluation with no recursion
                    evaluation = rawEvals[bestIndex]
                    
                    

                    #Sorry about the repetition
                    if (evaluation > bestEval and colour == "White") or (evaluation < bestEval and colour == "Black"): #new best move
                        bestEval = evaluation
                        bestMove = move

                    if colour == "White":
                        alpha = max(alpha, evaluation)
                        if alpha >= beta:
                            #print(alpha)
                            #print(beta)
                            #print("White")
                            return [bestMove, bestEval]
                    else:
                        beta = min(beta, evaluation)
                        if alpha >= beta:
                            #print(alpha)
                            #print(beta)
                            #print("Black")
                            return [bestMove, bestEval]

                #clean up the list so it doesn't repeat evaluations
                #NOTE: Popping causes sliding issues
                if colour == "White":
                    testRawEvals[bestIndex] = -9999999
                else:
                    testRawEvals[bestIndex] = 9999999

            if depth == 1:
                #limitedDepth += depthInc * 1/limitedDepth
                limitedDepth += 1
                
                
                print(bestMove)
                print(round(bestEval,2))
                
                #print(round(limitedDepth,1))
            if depth != 1: #only repeat if depth = 1
                break
        return [bestMove, bestEval]
        
    else: #No legal moves
        print("Not good")
        bestEval = -99999
        if colour == "Black":
            bestEval = -bestEval #for the other colour'''
        return [['P',[9,9],'-',[9,9]], bestEval]

            
    

#Initialise the board

#each side can either be player, easy, medium or hard. I'll play around with the difficulties later.

#Use a dictionary to store *most* piece values, since that's more professional and efficient
pieceValues = {
  'P': 1,
  'N': 3.1,
  'B': 3.4,
  'R': 5,
  'Q': 9,
  'K': 18 #if 9 works, I'm not 100% sure
}

piecePlaceValues = [1, 3.1, 3.4, 5, 9, 18]

pieceValuesStanding = {
  'P': 1,
  'N': 3.1,
  'B': 3.4,
  'R': 5,
  'Q': 9,
  'K': 20 #NOTE: could try 20 at some point
}

pieceOrder = {
  'P': 0, 
  'N': 1,
  'B': 2,
  'R': 3,
  'Q': 4,
  'K': 5
}

orderPiece = ['P','N','B','R','Q','K']

#TODO: Indirect square control
squareControlConstant = 0.0125
#Let's prioritise the key squares
kingSafetyConstant = 2
centreConstant = 2 #no wonder the knight keeps sacrificing itself 
castlingCost = 1
pinConstant = 0.01


fixtures = ["Hard", "Player"]
colours = ["White", "Black"]

pawnValues = [1, 1, 1.05, 1.1, 1.2, 1.5, 2, 9]
pawnValuesInner = [1, 1, 1.2, 1.4, 1.6, 2, 3, 9]

enPassant = [9,9]

#Initialise the board, and all its relevant information
board = [[[0 for k in range(8)] for j in range(8)] for i in range(2)]
board[0][0] = [4, 1, 0, 0, 0, 0, 7, 10]
board[0][1] = [2, 1, 0, 0, 0, 0, 7, 8]
board[0][2] = [3, 1, 0, 0, 0, 0, 7, 9]
board[0][3] = [5, 1, 0, 0, 0, 0, 7, 11]
board[0][4] = [6, 1, 0, 0, 0, 0, 7, 12]
board[0][5] = [3, 1, 0, 0, 0, 0, 7, 9]
board[0][6] = [2, 1, 0, 0, 0, 0, 7, 8]
board[0][7] = [4, 1, 0, 0, 0, 0, 7, 10]

#En Passant

board[1][0][0] = 9
board[1][1][0] = 9

#Castling rights, at [0][3] and [1][3] for white for 0-0-0 and 0-0 respectively, then at [4][3] and [5][3] for black.

#Obviously, castling is legal at the start of the game
board[1][0][3] = 1
board[1][1][3] = 1
board[1][4][3] = 1
board[1][5][3] = 1

'''board.append([['R',"White"],['P',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['P',"Black"],['R',"Black"]])
board.append([['N',"White"],['P',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['P',"Black"],['N',"Black"]])
board.append([['B',"White"],['P',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['P',"Black"],['B',"Black"]])
board.append([['Q',"White"],['P',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['P',"Black"],['Q',"Black"]])
board.append([['K',"White"],['P',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['P',"Black"],['K',"Black"]])
board.append([['B',"White"],['P',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['P',"Black"],['B',"Black"]])
board.append([['N',"White"],['P',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['P',"Black"],['N',"Black"]])
board.append([['R',"White"],['P',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['P',"Black"],['R',"Black"]])'''

'''board.append([['-',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['P',"Black"],['-',"White"],['-',"White"]])
board.append([['-',"White"],['-',"White"],['-',"White"],['-',"White"],['K',"Black"],['-',"White"],['-',"White"],['-',"White"]])
board.append([['-',"White"],['P',"White"],['-',"White"],['R',"White"],['-',"White"],['P',"White"],['N',"Black"],['-',"White"]])
board.append([['-',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"]])
board.append([['-',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"]])
board.append([['-',"White"],['K',"White"],['P',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"],['-',"White"]])
board.append([['-',"White"],['-',"White"],['-',"White"],['-',"White"],['P',"Black"],['B',"White"],['-',"White"],['-',"White"]])
board.append([['-',"White"],['-',"White"],['P',"White"],['-',"White"],['-',"White"],['P',"Black"],['-',"White"],['-',"White"]])'''


letters = ['a','b','c','d','e','f','g','h'] # for the sake of co-ordinates

badAttack = []
goodAttack = []

#Now we need to calculate and return all legal moves:

for turn in range(150):
    newBoard = board #please don't change

    for turnNo in range(2): #for white, then black
        pawnMult = 1 - turnNo*2
        colour = colours[turnNo]
        if colour == "White":
            otherColour = "Black"
        else:
            otherColour = "White"

        legalMoves = calculateLegalMoves(colour, newBoard)[0]
        confirmedLegalMoves = []

        for move in legalMoves:
            piece = move[0]

            testBoard = [[[newBoard[i][j][k] for k in range(8)] for j in range(8)] for i in range(2)] #copying a numpy array should be quick (hopefully)
            if move == [piece, [4, turnNo*7], '-', [2, turnNo*7]]:
                #try to castle queenside
                if testBoard[1][turnNo*4][3] == 1: #Can we legally castle queenside?
                    #Are the squares clear?
                    if testBoard[0][3][turnNo*7] == 0 and testBoard[0][2][turnNo*7] == 0 and testBoard[0][1][turnNo*7] == 0:
                        testMove = ['K', [4, turnNo*7], '-', [4, turnNo*7]] #cannot castle if in check!
                        if not isKingInCheck(testMove, testBoard, colour):
                            testMove = ['K', [4, turnNo*7], '-', [3, turnNo*7]]
                            if not isKingInCheck(testMove, testBoard, colour):
                                testMove = ['K', [3, turnNo*7], '-', [2, turnNo*7]] #Assuming the board is modified within the function
                                if not isKingInCheck(testMove, testBoard, colour):
                                    confirmedLegalMoves.append(move)

            elif move == [piece, [4, turnNo*7], '-', [6, turnNo*7]]:
                #try to castle kingside
                if testBoard[1][turnNo*4 + 1][3] == 1: #Can we legally castle kingside?
                    #Are the squares clear?
                    if testBoard[0][5][turnNo*7] == 0 and testBoard[0][6][turnNo*7] == 0:
                        testMove = ['K', [4, turnNo*7], '-', [4, turnNo*7]] #cannot castle if in check!
                        if not isKingInCheck(testMove, testBoard, colour):
                            testMove = ['K', [4, turnNo*7], '-', [5, turnNo*7]]
                            if not isKingInCheck(testMove, testBoard, colour):
                                testMove = ['K', [5, turnNo*7], '-', [6, turnNo*7]] #Assuming the board is modified within the function
                                if not isKingInCheck(testMove, testBoard, colour):
                                    confirmedLegalMoves.append(move)

            elif not isKingInCheck(move, testBoard, colour):
                confirmedLegalMoves.append(move)

        if fixtures[turnNo] == "Player":
            while(True):
                testMove = input("Your move: ")
                if len(testMove) != 6:
                    if testMove == "player moves" or testMove == "opponent moves":
                        if testMove == "player moves":
                            legalTestMoves = calculateLegalMoves(colour, testBoard)[0]
                        else:
                            legalTestMoves = calculateLegalMoves(otherColour, testBoard)[0]
                        for item in legalTestMoves:
                            printMove(turn, item)
                    elif testMove == 'board':
                        testBoard = [[[board[i][j][k] for k in range(8)] for j in range(8)] for i in range(2)]
                        printBoard(testBoard) #TODO: Print the actual board, not meaningless numbers (unless that takes you fancy)
                    else:
                        print("String is not 6 characters. Please try again (e.g. Rh1-h2)")
                else:
                    piece = testMove[0]
                    startSquare = [int(ord(testMove[1]) - 97),int(testMove[2])-1]
                    isCapture = testMove[3]
                    endSquare = [int(ord(testMove[4]) - 97),int(testMove[5])-1]
                    move = [piece, startSquare, isCapture, endSquare]
                    if move in confirmedLegalMoves:
                        break
                    else:
                        print("That move is illegal")

        else: #Not a human, use artificial intelligence for maximum brainpower
            
            #Jokes, it's just totally random
            if fixtures[turnNo] == "Random":
                if len(confirmedLegalMoves) > 0:
                    m = random.randint(0,len(confirmedLegalMoves)-1)
                    move = confirmedLegalMoves[m]
            
            else: #Any difficulty harder than medium
                #We gotta get recursive
                maxDepth = 3 #1 means no recursion (yet)
                depth = 1
                limitedDepth = 2
                depthInc = 1

                testBoard = [[[board[i][j][k] for k in range(8)] for j in range(8)] for i in range(2)]
                testTurnNo = turnNo

                #cProfile.run('minimaxSearch(testBoard, depth, testTurnNo, -999999999, 999999999, 0, limitedDepth)')
                
                [move, bestEval] = minimaxSearch(testBoard, depth, testTurnNo, -999999999, 999999999, 0, limitedDepth)
                #print(bestLine)
                #TODO: Plan out how to calculate the bestLine correctly.


                #bestEval = (1.000001)/(bestEval+0.00001)

                if bestEval >= 0:
                    print("+", end = "")
                    print(round(bestEval,2))
                else:
                    print(round(bestEval,2))


        if len(confirmedLegalMoves) > 0: #TODO: Make sure castling is performed correctly

            piece = move[0]

            if piece == 'K': #If the king moves, you can't castle
                board[1][turnNo*4][3] = 0 #Can't castle queenside from now on
                board[1][turnNo*4 + 1][3] = 0 #Can't castle kingside from now on
                board[1][turnNo*4][1] = 1 #The king has moved
                if abs(move[1][0] - move[3][0]) == 2: #if castling
                    board[1][turnNo*4][2] = 1 #The king is castled now

            if piece == 'R': #If the rook moves, you can't castle in that direction
                if move[1][0] == 0: #if x == 0, you can't castle queenside
                    board[1][turnNo*4][3] = 0 #Can't castle queenside from now on
                else:
                    board[1][turnNo*4 + 1][3] = 0 #Can't castle kingside from now on

            if piece == 'P' and abs(move[1][1]-move[3][1])==2: #If pawn moves 2 squares, en passant is possible next move
                x = move[1][0]
                y = int((move[1][1] + move[3][1])/2)
                board[1][0][0] = x #Entering en passant co-ordinates
                board[1][1][0] = y
            else:
                board[1][0][0] = 9 #En passant is now impossible
                board[1][1][0] = 9

            printMove(turn + 1, move)
            

            #now change the original board (really we should be changing a copy but not necessary yet)

            #make move 
            testBoard = board
            makeMove(move, testBoard, colour)  #This should change the original board too, if my understanding of pointers is correct
        else:
            print("No legal moves. Game over") 
            #TODO: Stalemate vs Checkmate
            break
    print()
