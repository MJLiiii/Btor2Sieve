(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x2276 (and (distinct s_6 (_ bv15 4)) true)))
(not $x2276)))
(check-sat)
