(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x5466 (bvule i_2 (_ bv1 4))))
(not $x5466)))
(check-sat)
