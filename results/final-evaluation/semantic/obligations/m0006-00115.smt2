(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x5406 (and (distinct s_3 (_ bv1 4)) true)))
(not $x5406)))
(check-sat)
