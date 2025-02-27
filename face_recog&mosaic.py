import cv2
import dlib
import threading
import time
import os
import face_recognition
import numpy as np
import copy

#Initialize a face cascade using the frontal face haar cascade provided with
#the OpenCV library
#Make sure that you copy this file from the opencv project to the root of this
#project folder
# faceCascade = cv2.CascadeClassifier('xmls/haarcascade_frontalface_default.xml')

#The deisred output width and height
OUTPUT_SIZE_WIDTH = 775
OUTPUT_SIZE_HEIGHT = 600
MOSAIC_RATE = 10
BASE_SIZE_WIDTH = 320
BASE_SIZE_HEIGHT = 240

known_face_encodings = []
known_face_names = []
faces_locations = []
face_encodings = []
face_names = {}

# Load sample pictures and learn how to recognize it.
dirname = 'knowns'
files = os.listdir(dirname)
for filename in files:
    name, ext = os.path.splitext(filename)
    if ext == '.jpg':
        known_face_names.append(name)
        pathname = os.path.join(dirname, filename)
        img = face_recognition.load_image_file(pathname)
        face_encoding = face_recognition.face_encodings(img)[0]
        known_face_encodings.append(face_encoding)


#We are not doing really face recognition
def doRecognizePerson(faceNames, fid):
    time.sleep(2)
    faceNames[ fid ] = "Person " + str(fid)

def detectAndTrackMultipleFaces():
    #Open the first webcame device
    capture = cv2.VideoCapture(0)

    #Create two opencv named windows
    cv2.namedWindow("base-image", cv2.WINDOW_AUTOSIZE)
    cv2.namedWindow("result-image", cv2.WINDOW_AUTOSIZE)
    cv2.namedWindow("mosaic-image", cv2.WINDOW_AUTOSIZE)

    #Position the windows next to eachother
    cv2.moveWindow("base-image",0,0)
    cv2.moveWindow("result-image",800,0)
    cv2.moveWindow("mosaic-image",0,0)

    #Start the window thread for the two windows we are using
    cv2.startWindowThread()

    #The color of the rectangle we draw around the face
    rectangleColor = (0,165,255)

    #variables holding the current frame number and the current faceid
    frameCounter = 0
    currentFaceID = 0

    #Variables holding the correlation trackers and the name per faceid
    faceTrackers = {}
    faceNames = {}
    frameList = []
    top_list = []
    bottom_list = []
    left_list = []
    right_list = []

    try:
        while True:
            #Retrieve the latest image from the webcam
            rc,fullSizeBaseImage = capture.read()

            #Resize the image to BASE_SIZE_WIDTHxBASE_SIZE_HEIGHT
            baseImage = cv2.resize( fullSizeBaseImage, ( BASE_SIZE_WIDTH, BASE_SIZE_HEIGHT))
            
            frameList.append(baseImage)
            if len(frameList) > 5 :
                del frameList[0]
            

            print("frame %d" % frameCounter)
            #Check if a key was pressed and if it was Q, then break
            #from the infinite loop
            if cv2.waitKey(1) & 0xFF == ord('Q') :
                quit()

            #Result image is the image we will show the user, which is a
            #combination of the original image from the webcam and the
            #overlayed rectangle for the largest face
            resultImage = baseImage.copy()
            mosaicImage = baseImage.copy()

            #STEPS:
            # * Update all trackers and remove the ones that are not 
            #   relevant anymore
            # * Every 10 frames:
            #       + Use face detection on the current frame and look
            #         for faces. 
            #       + For each found face, check if centerpoint is within
            #         existing tracked box. If so, nothing to do
            #       + If centerpoint is NOT in existing tracked box, then
            #         we add a new tracker with a new face-id


            #Increase the framecounter
            frameCounter += 1 


            #Update all the trackers and remove the ones for which the update
            #indicated the quality was not good enough
            fidsToDelete = []
            for fid in faceTrackers.keys():
                trackingQuality = faceTrackers[ fid ].update( baseImage )

                #If the tracking quality is good enough, we must delete
                #this tracker
                if trackingQuality < 5:
                    fidsToDelete.append( fid )

            for fid in fidsToDelete:
                print("Removing fid " + str(fid) + " from list of trackers")
                faceTrackers.pop( fid , None )
                face_names.pop(fid, None)

            #Every 5 frames, we will have to determine which faces
            #are present in the frame
            if (frameCounter % 5) == 0:

                #For the face detection, we need to make use of a gray
                #colored image so we will convert the baseImage to a
                #gray-based image
                # gray = cv2.cvtColor(baseImage, cv2.COLOR_BGR2GRAY)
                #Now use the haar cascade detector to find all faces
                #in the image
                # faces = faceCascade.detectMultiScale(gray, 1.3, 5)

                faces = face_recognition.face_locations(baseImage)
                # face_encodings = face_recognition.face_encodings(baseImage, faces)

                # print(faceTrackers[0])
                # print(face_encodings)


                #Loop over all faces and check if the area for this
                #face is the largest so far
                #We need to convert it to int here because of the
                #requirement of the dlib tracker. If we omit the cast to
                #int here, you will get cast errors since the detector
                #returns numpy.int32 and the tracker requires an int
                for (top, right, bottom, left) in faces:
                    x = int(left)
                    y = int(top)
                    w = int(right - left)
                    h = int(bottom - top)


                    #calculate the centerpoint
                    x_bar = x + 0.5 * w
                    y_bar = y + 0.5 * h



                    #Variable holding information which faceid we 
                    #matched with
                    matchedFid = None

                    #Now loop over all the trackers and check if the 
                    #centerpoint of the face is within the box of a 
                    #tracker
                    for fid in faceTrackers.keys():
                        tracked_position =  faceTrackers[fid].get_position()

                        t_x = int(tracked_position.left())
                        t_y = int(tracked_position.top())
                        t_w = int(tracked_position.width())
                        t_h = int(tracked_position.height())


                        #calculate the centerpoint
                        t_x_bar = t_x + 0.5 * t_w
                        t_y_bar = t_y + 0.5 * t_h

                        #check if the centerpoint of the face is within the 
                        #rectangleof a tracker region. Also, the centerpoint
                        #of the tracker region must be within the region 
                        #detected as a face. If both of these conditions hold
                        #we have a match
                        if ( ( t_x <= x_bar   <= (t_x + t_w)) and 
                             ( t_y <= y_bar   <= (t_y + t_h)) and 
                             ( x   <= t_x_bar <= (x   + w  )) and 
                             ( y   <= t_y_bar <= (y   + h  ))):
                            matchedFid = fid


                    #If no matched fid, then we have to create a new tracker
                    if matchedFid is None:

                        print("Creating new tracker " + str(currentFaceID))

                        #Create and store the tracker 
                        tracker = dlib.correlation_tracker()
                        tracker.start_track(baseImage,
                                            dlib.rectangle( x-10,
                                                            y-20,
                                                            x+w+10,
                                                            y+h+20))

                        faceTrackers[ currentFaceID ] = tracker
                        face_encodings = face_recognition.face_encodings(baseImage, [(top, right, bottom, left)])

                        distances = face_recognition.face_distance(known_face_encodings, face_encodings[0])
                        min_value = min(distances)

                        # tolerance: How much distance between faces to consider it a match. Lower is more strict.
                        # 0.6 is typical best performance.
                        name = "Unknown"
                        if min_value < 0.4:
                            index = np.argmin(distances)
                            name = known_face_names[index]

                        face_names[ currentFaceID ] = name

                        print(face_names)

                        #Start a new thread that is used to simulate 
                        #face recognition. This is not yet implemented in this
                        #version :)
                        t = threading.Thread( target = doRecognizePerson ,
                                               args=(faceNames, currentFaceID))
                        t.start()

                        #Increase the currentFaceID counter
                        currentFaceID += 1

            #Now loop over all the trackers we have and draw the rectangle
            #around the detected faces. If we 'know' the name for this person
            #(i.e. the recognition thread is finished), we print the name
            #of the person, otherwise the message indicating we are detecting
            #the name of the person
            for fid in faceTrackers.keys():
                tracked_position =  faceTrackers[fid].get_position()
                # print(tracked_position)
                t_x = int(tracked_position.left())
                t_y = int(tracked_position.top())
                t_w = int(tracked_position.width())
                t_h = int(tracked_position.height())

                cv2.rectangle(resultImage, (t_x, t_y),
                                        (t_x + t_w , t_y + t_h),
                                        rectangleColor ,2)

                m_x = int(t_x > 0 and t_x or 0)
                m_y = int(t_y > 0 and t_y or 0)
                m_w = int(t_x + t_w < BASE_SIZE_WIDTH and t_w or BASE_SIZE_WIDTH - t_x)
                m_h = int(t_y + t_h < BASE_SIZE_HEIGHT and t_h or BASE_SIZE_HEIGHT - t_y)

                top_list.append(m_y)
                bottom_list.append(m_y + m_h)
                left_list.append(m_x)
                right_list.append(m_x + m_w)

                
                if len(top_list) > 5:
                    del top_list[0]
                    del bottom_list[0]
                    del left_list[0]
                    del right_list[0]

                c_top_list = copy.deepcopy(top_list)
                c_bottom_list = copy.deepcopy(bottom_list)
                c_left_list = copy.deepcopy(left_list)
                c_right_list = copy.deepcopy(right_list)

                c_top_list.sort()
                c_bottom_list.reverse()
                c_left_list.sort()
                c_right_list.reverse()
                

                if(face_names[fid] == 'Unknown'):
                    face_img = frameList[0][c_top_list[0]:c_bottom_list[0], c_left_list[0]:c_right_list[0]]
                    face_img = cv2.resize(face_img, ((c_right_list[0]-c_left_list[0])//MOSAIC_RATE, (c_bottom_list[0] - c_top_list[0])//MOSAIC_RATE))
                    face_img = cv2.resize(face_img, (c_right_list[0]-c_left_list[0], c_bottom_list[0] - c_top_list[0]), interpolation=cv2.INTER_AREA)
                    frameList[0][c_top_list[0]:c_bottom_list[0], c_left_list[0]:c_right_list[0]] = face_img

                # if(face_names[fid] == 'Unknown'):
                #     # face_img = mosaicImage[m_y:m_y + m_h, m_x:m_x + m_w]
                #     face_img = frameList[0][m_y:m_y + m_h, m_x:m_x + m_w]
                #     face_img = cv2.resize(face_img, (m_w//MOSAIC_RATE, m_h//MOSAIC_RATE))
                #     face_img = cv2.resize(face_img, (m_w, m_h), interpolation=cv2.INTER_AREA)
                #     # mosaicImage[m_y:m_y + m_h, m_x:m_x + m_w] = face_img
                #     frameList[0][m_y:m_y + m_h, m_x:m_x + m_w] = face_img



                if fid in faceNames.keys():
                    cv2.putText(resultImage, face_names[fid] , 
                                (int(t_x + t_w/2), int(t_y)), 
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, (255, 255, 255), 2)
                else:
                    cv2.putText(resultImage, "Detecting..." , 
                                (int(t_x + t_w/2), int(t_y)), 
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, (255, 255, 255), 2)

            #Since we want to show something larger on the screen than the
            #original BASE_SIZE_WIDTHxBASE_SIZE_HEIGHT, we resize the image again
            #
            #Note that it would also be possible to keep the large version
            #of the baseimage and make the result image a copy of this large
            #base image and use the scaling factor to draw the rectangle
            #at the right coordinates.
            largeResult = cv2.resize(resultImage,
                                     (OUTPUT_SIZE_WIDTH,OUTPUT_SIZE_HEIGHT))
            # mosaicResult = cv2.resize(mosaicImage,
            #                          (OUTPUT_SIZE_WIDTH,OUTPUT_SIZE_HEIGHT))
            mosaicResult = cv2.resize(frameList[0],
                                     (OUTPUT_SIZE_WIDTH,OUTPUT_SIZE_HEIGHT))

            #Finally, we want to show the images on the screen
            cv2.imshow("base-image", baseImage)
            cv2.imshow("result-image", largeResult)
            if len(frameList) == 5:
                cv2.imshow("mosaic-image", mosaicResult)

    #To ensure we can also deal with the user pressing Ctrl-C in the console
    #we have to check for the KeyboardInterrupt exception and break out of
    #the main loop
    except KeyboardInterrupt as e:
        pass

    #Destroy any OpenCV windows and exit the application
    cv2.destroyAllWindows()
    exit(0)

if __name__ == '__main__':
    detectAndTrackMultipleFaces()