(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x72 (bvuge i_7 (_ bv1 8))))
(not $x72)))
(check-sat)
