"""Face encoding/matching directly dlib se (face_recognition package ki zaroorat nahi).
Isse Vercel/Linux par dlib source-build ki dikkat nahi aati."""
import numpy as np
import dlib
import face_recognition_models as m

_detector = dlib.get_frontal_face_detector()
_shape = dlib.shape_predictor(m.pose_predictor_five_point_model_location())
_rec = dlib.face_recognition_model_v1(m.face_recognition_model_location())

def face_encodings(img):
    """img: RGB numpy array -> har chehre ka 128-number encoding"""
    return [np.array(_rec.compute_face_descriptor(img, _shape(img, d), 1))
            for d in _detector(img, 1)]

def face_distance(known, enc):
    return np.linalg.norm(np.array(known) - enc, axis=1)
