(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x5186 (bvule i_6 (_ bv128 8))))
(not $x5186)))
(check-sat)
