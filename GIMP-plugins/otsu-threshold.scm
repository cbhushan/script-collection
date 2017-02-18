;; Largely based on
;; * gimp_histogram_get_threshold() in https://github.com/GNOME/gimp/blob/fc9da4c9a394ef981a32973e9ee6f82a224905e2/app/core/gimphistogram.c
;; * http://stackoverflow.com/a/8462738
;;
;; Released under MIT License
;; https://github.com/cbhushan/script-collection
;;
;; Copyright (c) 2017 C Bhushan
;;
;; Permission is hereby granted, free of charge, to any person obtaining a copy
;; of this software and associated documentation files (the "Software"), to deal
;; in the Software without restriction, including without limitation the rights
;; to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
;; copies of the Software, and to permit persons to whom the Software is
;; furnished to do so, subject to the following conditions:
;;
;; The above copyright notice and this permission notice shall be included in all
;; copies or substantial portions of the Software.
;;
;; THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
;; IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
;; FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
;; AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
;; LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
;; OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
;; SOFTWARE.


(define (script-fu-otsu-threshold image)
  (gimp-undo-push-group-start image)
  (let* ((drawable (car (gimp-image-flatten image)))
	 (thresh 100)
	 )
    (gimp-layer-flatten drawable)
    (gimp-image-convert-grayscale image)
					;(if (gimp-drawable-is-gray drawable)
					;   ()
					;
					;     )
    (let* ((hist (get-hist drawable 0))
	   )
      (set! thresh (get-otsu-threshold hist))
      )
    (gimp-threshold drawable thresh 255)
    (gimp-image-convert-indexed image 0 3 2 0 1 "ignoredtext")
    )
  (gimp-undo-push-group-end image)
  )

;; Returns the Otsu threshold
;; * N. Otsu, "A threshold selection method from gray-level histograms,"
;;     IEEE Trans. Systems, Man, and Cybernetics, vol. 9, no. 1, pp. 62-66, 1979.
;; * https://en.wikipedia.org/wiki/Otsu's_method
(define (get-otsu-threshold hist) 
  (let*
      (
       (hist_max (vector-ref hist 0))
       (chist (make-vector 256)) ;; Cummulative histogram - \omega_0(t)
       (cmom (make-vector 256)) ;; cummulative mean (1st order moment) - \mu_0(t)*\omega_0(t)
       (maxval 255) ;; Go through all intensity
       (i 1)
       (chist_max)
       (cmom_max)
       (bvar_max 0)
       (threshold 127)
       )

    ;; Compute cummulative histogram and mean
    (vector-set! chist 0 (vector-ref hist 0))
    (vector-set! cmom 0 0)
    (set! i 1)
    (while (<= i maxval)
	   (if (> (vector-ref hist i) hist_max)
	       (set! hist_max (vector-ref hist i))
	       )
	   (vector-set! chist i (+ (vector-ref chist (- i 1)) (vector-ref hist i)) ) ;; \omega_0(t)
	   (vector-set! cmom i (+ (vector-ref cmom (- i 1)) (* i (vector-ref hist i))) ) ;; \mu_0(t)*\omega_0(t)
	   (set! i (+ i 1))
	   )

    (set! chist_max (vector-ref chist maxval))
    (set! cmom_max (vector-ref cmom maxval))

    ;; Iterate through all intensities and compute between-class variance.
    ;; Record intensity with max between-class variance.
    ;; bvar(t) = \omega_0(t) * \omega_1(t) * [\mu_0(t)-\mu_1(t)]^2
    (set! i 0)
    (while (< i maxval)
	   (if (and (> (vector-ref chist i) 0) (< (vector-ref chist i) chist_max) ) ;; Only compute between actual max & min intensity of the image
	       (let* 
		   ((bvar (/ (vector-ref cmom i) (vector-ref chist i)))) ;; bvar = \mu_0(t)
		 
		 (set! bvar (- bvar (/ (- cmom_max (vector-ref cmom i)) (- chist_max (vector-ref chist i)) ) )) ;; bvar := bvar - \mu_1(t) = [\mu_0(t)-\mu_1(t)]
		 (set! bvar (* bvar bvar)) ;; bvar := bvar^2 = [\mu_0(t)-\mu_1(t)]^2
		 (set! bvar (* bvar (vector-ref chist i)) ) ;; bvar := bvar * \omega_0(t) = \omega_0(t) * [\mu_0(t)-\mu_1(t)]^2
		 (set! bvar (* bvar (- chist_max (vector-ref chist i)) )) ;; bvar:= bvar*\omega_1(t) = \omega_0(t) * \omega_1(t) * [\mu_0(t)-\mu_1(t)]^2
		 
		 (if (> bvar bvar_max)
		     (begin
		       (set! threshold i)
		       (set! bvar_max bvar)
		       )
		     )
		 )
	       )
	   (set! i (+ i 1))
	   )
    threshold
    )
  )


;; Get the histogram count in an array
(define (get-hist drawable chan)
  (let* (
	 (i 0)
	 (hist (make-vector 256))
	 )
    (set! i 0)
    (while (< i 256)
	   (vector-set! hist i (car (cddddr (gimp-histogram drawable chan i i))))
	   (set! i (+ i 1))
	   )
    hist
    )
  )


(script-fu-register "script-fu-otsu-threshold"
  "Otsu threshold - binarize Image"
  "Apply Otsu thresholding to binarize image."
  "C Bhushan"
  "C Bhushan - MIT License"
  "2017"
  "*"
  SF-IMAGE      "The image"   0
;  SF-DRAWABLE   "The drawable"   0
  SF-TOGGLE     "Anti-aliasing (AA)"      FALSE
  SF-ADJUSTMENT "AA strength" (list 1 0 20 1 10 1 SF-SLIDER)
)

(script-fu-menu-register "script-fu-otsu-threshold"
                         "<Image>/Filters/Scanned Document")
