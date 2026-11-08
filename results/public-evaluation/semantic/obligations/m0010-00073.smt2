(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 1))
(assert
 true)
(assert
 (let (($x30 (and (distinct i_2 (_ bv1 1)) true)))
(not $x30)))
(check-sat)
