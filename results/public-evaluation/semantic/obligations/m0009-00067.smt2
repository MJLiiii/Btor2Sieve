(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x2316 (and (distinct s_7 (_ bv0 8)) true)))
(not $x2316)))
(check-sat)
