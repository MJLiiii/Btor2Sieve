(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x790 (and (distinct s_7 (_ bv1 8)) true)))
(not $x790)))
(check-sat)
