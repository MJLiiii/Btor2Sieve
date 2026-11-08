(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x2944 (and (distinct s_4 (_ bv15 4)) true)))
(not $x2944)))
(check-sat)
