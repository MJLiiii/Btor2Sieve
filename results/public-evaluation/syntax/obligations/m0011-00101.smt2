(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x1103 (and (distinct s_6 (_ bv1 4)) true)))
(not $x1103)))
(check-sat)
