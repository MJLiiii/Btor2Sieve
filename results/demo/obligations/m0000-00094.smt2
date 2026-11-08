(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x103 (and (distinct s_5 (_ bv255 8)) true)))
(not $x103)))
(check-sat)
