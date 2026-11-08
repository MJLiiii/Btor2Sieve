(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x43 (bvuge i_7 (_ bv128 8))))
(not $x43)))
(check-sat)
