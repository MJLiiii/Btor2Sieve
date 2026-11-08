(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x17 (bvule i_7 (_ bv128 8))))
(not $x17)))
(check-sat)
