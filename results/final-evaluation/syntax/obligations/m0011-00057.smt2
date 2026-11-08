(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x418 (and (distinct i_2 (_ bv1 4)) true)))
(not $x418)))
(check-sat)
