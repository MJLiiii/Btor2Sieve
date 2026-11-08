(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x229 (and (distinct i_4 (_ bv1 3)) true)))
(not $x229)))
(check-sat)
