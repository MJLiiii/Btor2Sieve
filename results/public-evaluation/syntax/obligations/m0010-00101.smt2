(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x2115 (bvule i_6 (_ bv1 8))))
(not $x2115)))
(check-sat)
