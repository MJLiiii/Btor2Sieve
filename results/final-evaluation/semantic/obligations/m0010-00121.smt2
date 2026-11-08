(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x174 (bvule i_7 (_ bv1 8))))
(not $x174)))
(check-sat)
